#!/usr/bin/env python

# Copyright (C) 2011-2013 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
# Author: tasleson

#Description:   Query array capabilities and run very basic operational tests.
#
# Note: This file is GPL copyright and not LGPL because:
# 1. It is used to test the library, not provide functionality for it.
# 2. It uses a function copied from anaconda library which is GPLv2 or later,
#    thus this code must be GPL as well.

import random
import string
import sys
import hashlib
import os
from subprocess import Popen, PIPE
from optparse import OptionParser


(OP_SYS, OP_POOL, OP_VOL, OP_INIT, OP_FS, OP_EXPORTS, OP_SS) = \
    ('SYSTEMS', 'POOLS', 'VOLUMES', 'INITIATORS', 'FS', 'EXPORTS',
     'SNAPSHOTS')

(ID, NAME) = (0, 1)
(POOL_TOTAL, POOL_FREE, POOL_SYSTEM) = (2, 3, 4)
(VOL_VPD, VOL_BS, VOL_BLOCKS, VOL_STATUS, VOL_SIZE) = (2, 3, 4, 5, 6)
(INIT_TYPE) = 2
(FS_TOTAL, FS_FREE, FS_POOL_ID) = (2, 3, 4)

(SYS_STATUS,) = (2,)

iqn = ['iqn.1994-05.com.domain:01.89bd01', 'iqn.1994-05.com.domain:01.89bd02']

cmd = "lsmcli"

sep = ","
test_pool_name = 'lsm_test_aggr'
test_fs_pool_id = ''

CUR_SYS_ID = None

code_coverage = bool(os.getenv('LSM_PYTHON_COVERAGE', False))


def random_iqn():
    """Logic taken from anaconda library"""

    s = "iqn.1994-05.com.domain:01."
    m = hashlib.md5()
    u = os.uname()
    for i in u:
        m.update(i)
    dig = m.hexdigest()

    for i in range(0, 6):
        s += dig[random.randrange(0, 32)]
    return s


def rs(l):
    """
    Generate a random string
    """
    return 'lsm_' + ''.join(
        random.choice(string.ascii_uppercase) for x in range(l))


def call(command, expected_rc=0):
    """
    Call an executable and return a tuple of exitcode, stdout, stderr
    """

    if code_coverage:
        actual_command = ['coverage', 'run', '-a']
        actual_command.extend(command)
    else:
        actual_command = command

    print actual_command, 'EXPECTED Exit [%d]' % expected_rc

    process = Popen(actual_command, stdout=PIPE, stderr=PIPE)
    out = process.communicate()

    if process.returncode != expected_rc:
        raise RuntimeError("exit code != %s, actual= %s, stdout= %s, "
                           "stderr= %s" % (expected_rc, process.returncode,
                                           out[0], out[1]))
    return process.returncode, out[0], out[1]


def parse(out):
    rc = []
    for line in out.split('\n'):
        elem = line.split(sep)
        if len(elem) > 1:
            rc.append(elem)
    return rc


def parse_display(op):
    rc = []
    out = call([cmd, '-t' + sep, 'list', '--type', op])[1]
    for line in out.split('\n'):
        elem = line.split(sep)
        if len(elem) > 1:
            rc.append(elem)
    return rc


def name_to_id(op, name):
    out = parse_display(op)

    for i in out:
        if i[NAME] == name:
            return i[ID]
    return None


def create_volume(pool):
    out = call([cmd, '-t' + sep, 'create-volume', '--name', rs(12), '--size',
                '30M', '--pool', pool, '--provisioning', 'DEFAULT'])[1]
    r = parse(out)
    return r[0][ID]


def delete_volume(vol_id):
    call([cmd, '-t' + sep, '-f', 'delete-volume', '--id', vol_id])


def create_fs(pool_id):
    out = call([cmd, '-t' + sep, 'create-fs', '--name', rs(12), '--size',
                '500M', '--pool', pool_id])[1]
    r = parse(out)
    return r[0][ID]


def delete_fs(init_id):
    call([cmd, '-t' + sep, '-f', 'delete-fs', '--fs_id', init_id])


def create_access_group(init_id, system_id):
    out = call([cmd, '-t' + sep, 'create-access-group', '--name', rs(8),
                '--id', init_id, '--type', 'ISCSI', '--system', system_id])[1]
    r = parse(out)
    return r[0][ID]


def access_group_add_init(group, initiator):
    call([cmd, 'access-group-add', '--gid', group, '--iid', initiator,
          '--type', 'ISCSI'])


def access_group_remove_init(group, initiator):
    call([cmd, 'access-group-remove', '--gid', group, '--iid', initiator])


# TODO Change --group_id to --gid to be consistent ?
def delete_access_group(group_id):
    call([cmd, '-t' + sep, 'delete-access-group', '--group_id', group_id ])


def access_group_grant(group, volume_id):
    call([cmd, 'access-grant-group', '--id', group, '--volume', volume_id,
          '--access', 'RW'])


def access_group_revoke(group, volume_id):
    call([cmd, 'access-revoke-group', '--id', group, '--volume', volume_id])


def volumes_accessible_by_access_group(ag_id):
    call([cmd, 'access-group-volumes', '--gid', ag_id])


def volume_accessible_by_initiator(iqn2):
    call([cmd, 'volumes-accessible-initiator', '--iid', iqn2])


def initiators_granted_to_volume(vol):
    call([cmd, 'initiators-granted-volume', '--vol_id', vol])


def access_groups_granted_to_volume(vol_id):
    call([cmd, 'volume-access-group', '--vol_id', vol_id])


def resize_vol(init_id):
    call([cmd, '-t' + sep, '-f',
          'resize-volume',
          '--id', init_id,
          '--size', '60M'])
    call([cmd, '-t' + sep, '-f',
          'resize-volume',
          '--id', init_id,
          '--size', '100M'])
    #Some devices cannot re-size down...
    #call([cmd, '--resize-volume', id, '--size', '30M' , '-t'+sep ])


def resize_fs(init_id):
    call([cmd, '-t' + sep, '-f',
          'resize-fs',
          '--id', init_id,
          '--size', '1G'])
    call([cmd, '-t' + sep, '-f',
          'resize-fs',
          '--id', init_id,
          '--size', '750M'])
    call([cmd, '-t' + sep, '-f',
          'resize-fs',
          '--id', init_id,
          '--size', '300M'])


def map_init(init, volume):
    call([cmd, '-t' + sep, 'access-grant', '--id', init, '--volume', volume,
          '--access', 'RW'])


def unmap(init, volume):
    call([cmd, 'access-revoke', '--id', init, '--volume', volume])


def clone_fs(fs_id):
    # TODO Change to --source_id instead of --source_name ?
    out = call([cmd, '-t' + sep, 'clone-fs', '--source_name', fs_id,
                '--dest_name', 'cloned_' + rs(8)])[1]
    r = parse(out)
    return r[0][ID]


def fs_child_dependancy(fs_id):
    call([cmd, 'fs-dependants', '--id', fs_id])


def fs_child_dependancy_rm(fs_id):
    call([cmd, 'fs-dependants-rm', '--id', fs_id])


def clone_file(fs_id):
    # TODO Make this work outside of the simulator
    call([cmd, 'clone-file', '--fs', fs_id, '--src', 'foo', '--dest', 'bar'])


def create_ss(fs_id):
    out = call([cmd, '-t' + sep, 'create-ss', '--name', rs(12), '--fs',
                fs_id])[1]
    r = parse(out)
    return r[0][ID]


def delete_ss(fs_id, ss_id):
    call([cmd, '-f', 'delete-ss', '--id', ss_id, '--fs', fs_id])


def restore_ss(snapshot_id, fs_id):
    call([cmd, '-f', 'restore-ss', '--id', snapshot_id, '--fs', fs_id])


def replicate_volume(source_id, vol_type, pool=None):
    out = call([cmd,
                '-t' + sep,
                'replicate-volume',
                '--id', source_id,
                '--type', vol_type,
                '--name', 'lun_' + vol_type + '_' + rs(12)])[1]
    r = parse(out)
    return r[0][ID]


def replicate_volume_range_bs(system_id):
    """
    Returns the replicated range block size.
    """
    out = call([cmd,
                'replicate-volume-range-block-size',
                '--id', system_id])[1]
    return int(out)


def replicate_volume_range(vol_id, dest_vol_id, rep_type, src_start,
                           dest_start, count):
    out = call(
        [cmd, '-f', 'replicate-volume-range',
            '--src', vol_id,
            '--type', rep_type,
            '--dest', dest_vol_id,
            '--src_start', str(src_start),
            '--dest_start', str(dest_start),
            '--count', str(count)])


def volume_child_dependency(vol_id):
    call([cmd, 'volume-dependants', '--id', vol_id])


def volume_child_dependency_rm(vol_id):
    call([cmd, 'volume-dependants-rm', '--id', vol_id])


def get_systems():
    out = call([cmd, '-t' + sep, 'list', '--type', 'SYSTEMS'])[1]
    system_list = parse(out)
    return system_list


def initiator_grant(initiator_id, vol_id):
#initiator_grant(self, initiator_id, initiator_type, volume, access,
#   flags = 0):
    call([cmd,
          'access-grant',
          '--id', initiator_id,
          '--type', 'ISCSI',
          '--volume', vol_id,
          '--access', 'RW'])


def initiator_chap(initiator):
    call([cmd, 'iscsi-chap',
          '--iid', initiator])
    call([cmd, 'iscsi-chap',
          '--iid', initiator,
          '--in-user', "foo",
          '--in-password', "bar"])
    call([cmd, 'iscsi-chap',
          '--iid', initiator, '--in-user', "foo",
          '--in-password', "bar", '--out-user', "foo",
          '--out-password', "bar"])


def initiator_revoke(initiator_id, vol_id):
    call([cmd, 'access-revoke',
                '--id', initiator_id,
                '--volume', vol_id])


def capabilities(system_id):
    """
    Return a hash table of key:bool where key is supported operation
    """
    rc = {}
    out = call([cmd, '-t' + sep, 'capabilities', '--system_id', system_id])[1]
    results = parse(out)

    for r in results:
        rc[r[0]] = True if r[1] == 'SUPPORTED' else False
    return rc


def get_existing_fs(system_id):
    out = call([cmd, '-t' + sep, 'list', '--type', 'FS', ])[1]
    results = parse(out)

    if len(results) > 0:
        return results[0][ID]
    return None


def numbers():
    vols = []
    test_pool_id = name_to_id(OP_POOL, test_pool_name)

    for i in range(10):
        vols.append(create_volume(test_pool_id))

    for i in vols:
        delete_volume(i)


def display_check(display_list, system_id):
    s = [x for x in display_list if x != 'SNAPSHOTS']
    for p in s:
        call([cmd, 'list', '--type', p])
        call([cmd, '-H', 'list', '--type', p, ])
        call([cmd, '-H', '-t' + sep, 'list', '--type', p])

    if 'SNAPSHOTS' in display_list:
        fs_id = get_existing_fs(system_id)
        if fs_id:
            call([cmd, 'list', '--type', 'SNAPSHOTS', '--fs', fs_id])

    if 'POOLS' in display_list:
        call([cmd, '-H', '-t' + sep, 'list', '--type', 'POOLS', '-o'])


def test_display(cap, system_id):
    """
    Crank through supported display operations making sure we get good
    status for each of them
    """
    to_test = ['SYSTEMS']

    if cap['BLOCK_SUPPORT']:
        to_test.append('POOLS')
        to_test.append('VOLUMES')

    if cap['FS_SUPPORT'] and cap['FS']:
        to_test.append("FS")

    if cap['INITIATORS']:
        to_test.append("INITIATORS")

    if cap['EXPORTS']:
        to_test.append("EXPORTS")

    if cap['ACCESS_GROUP_LIST']:
        to_test.append("ACCESS_GROUPS")

    if cap['FS_SNAPSHOTS']:
        to_test.append('SNAPSHOTS')

    if cap['EXPORT_AUTH']:
        to_test.append('NFS_CLIENT_AUTH')

    if cap['EXPORTS']:
        to_test.append('EXPORTS')

    display_check(to_test, system_id)


def test_block_creation(cap, system_id):
    vol_src = None
    test_pool_id = name_to_id(OP_POOL, test_pool_name)

    # Fail early if no pool is available
    if test_pool_id is None:
        print 'Pool %s is not available!' % test_pool_name
        exit(10)

    if cap['VOLUME_CREATE']:
        vol_src = create_volume(test_pool_id)

    if cap['VOLUME_RESIZE']:
        resize_vol(vol_src)

    if cap['VOLUME_REPLICATE'] and cap['VOLUME_DELETE']:
        if cap['VOLUME_REPLICATE_CLONE']:
            clone = replicate_volume(vol_src, 'CLONE', test_pool_id)
            delete_volume(clone)

        if cap['VOLUME_REPLICATE_COPY']:
            copy = replicate_volume(vol_src, 'COPY', test_pool_id)
            delete_volume(copy)

        if cap['VOLUME_REPLICATE_MIRROR_ASYNC']:
            m = replicate_volume(vol_src, 'MIRROR_ASYNC', test_pool_id)
            delete_volume(m)

        if cap['VOLUME_REPLICATE_MIRROR_SYNC']:
            m = replicate_volume(vol_src, 'MIRROR_SYNC', test_pool_id)
            delete_volume(m)

        if cap['VOLUME_COPY_RANGE_BLOCK_SIZE']:
            size = replicate_volume_range_bs(system_id)
            print 'sub volume replication block size is=', size

        if cap['VOLUME_COPY_RANGE']:
            if cap['VOLUME_COPY_RANGE_CLONE']:
                replicate_volume_range(vol_src, vol_src, "CLONE",
                                       0, 10000, 100)

            if cap['VOLUME_COPY_RANGE_COPY']:
                replicate_volume_range(vol_src, vol_src, "COPY",
                                       0, 10000, 100)

    if cap['VOLUME_CHILD_DEPENDENCY']:
        volume_child_dependency(vol_src)

    if cap['VOLUME_CHILD_DEPENDENCY_RM']:
        volume_child_dependency_rm(vol_src)

    if cap['VOLUME_DELETE']:
        delete_volume(vol_src)


def test_fs_creation(cap, system_id):

    if test_fs_pool_id:
        pool_id = test_fs_pool_id
    else:
        pool_id = name_to_id(OP_POOL, test_pool_name)

    if cap['FS_CREATE']:
        fs_id = create_fs(pool_id)

        if cap['FS_RESIZE']:
            resize_fs(fs_id)

        if cap['FS_DELETE']:
            delete_fs(fs_id)

    if cap['FS_CLONE']:
        fs_id = create_fs(pool_id)
        clone = clone_fs(fs_id)
        test_display(cap, system_id)
        delete_fs(clone)
        delete_fs(fs_id)

    if cap['FILE_CLONE']:
        fs_id = create_fs(pool_id)
        clone_file(fs_id)
        test_display(cap, system_id)
        delete_fs(fs_id)

    if cap['FS_SNAPSHOT_CREATE'] and cap['FS_CREATE'] and cap['FS_DELETE'] \
            and cap['FS_SNAPSHOT_DELETE']:
        #Snapshot create/delete
        fs_id = create_fs(pool_id)
        ss = create_ss(fs_id)
        test_display(cap, system_id)
        restore_ss(ss, fs_id)
        delete_ss(fs_id, ss)
        delete_fs(fs_id)

    if cap['FS_CHILD_DEPENDENCY']:
        fs_id = create_fs(pool_id)
        fs_child_dependancy(fs_id)
        delete_fs(fs_id)

    if cap['FS_CHILD_DEPENDENCY_RM']:
        fs_id = create_fs(pool_id)
        fs_child_dependancy_rm(fs_id)
        delete_fs(fs_id)


def test_mapping(cap, system_id):
    pool_id = name_to_id(OP_POOL, test_pool_name)
    iqn1 = random_iqn()
    iqn2 = random_iqn()

    if cap['ACCESS_GROUP_CREATE']:
        ag_id = create_access_group(iqn1, system_id)

        if cap['ACCESS_GROUP_ADD_INITIATOR']:
            access_group_add_init(ag_id, iqn2)

        if cap['ACCESS_GROUP_GRANT'] and cap['VOLUME_CREATE']:
            vol_id = create_volume(pool_id)
            access_group_grant(ag_id, vol_id)

            test_display(cap, system_id)

            if cap['VOLUMES_ACCESSIBLE_BY_ACCESS_GROUP']:
                volumes_accessible_by_access_group(ag_id)

            if cap['VOLUME_ACCESSIBLE_BY_INITIATOR']:
                volume_accessible_by_initiator(iqn2)

            if cap['INITIATORS_GRANTED_TO_VOLUME']:
                initiators_granted_to_volume(vol_id)

            if cap['ACCESS_GROUPS_GRANTED_TO_VOLUME']:
                access_groups_granted_to_volume(vol_id)

            if cap['ACCESS_GROUPS_GRANTED_TO_VOLUME']:
                access_groups_granted_to_volume(vol_id)

            if cap['ACCESS_GROUP_REVOKE']:
                access_group_revoke(ag_id, vol_id)

            if cap['VOLUME_DELETE']:
                delete_volume(vol_id)

            if cap['ACCESS_GROUP_DEL_INITIATOR']:
                access_group_remove_init(ag_id, iqn1)
                access_group_remove_init(ag_id, iqn2)

            if cap['ACCESS_GROUP_DELETE']:
                delete_access_group(ag_id)

    if cap['VOLUME_INITIATOR_GRANT']:
        vol_id = create_volume(pool_id)
        initiator_grant(iqn1, vol_id)

        test_display(cap, system_id)

        if cap['VOLUME_ISCSI_CHAP_AUTHENTICATION']:
            initiator_chap(iqn1)

        if cap['VOLUME_INITIATOR_REVOKE']:
            initiator_revoke(iqn1, vol_id)

        if cap['VOLUME_DELETE']:
            delete_volume(vol_id)


def test_nfs_operations(cap, system_id):
    pass


def test_plugin_info(cap, system_id):
    out = call([cmd, 'plugin-info', ])[1]
    out = call([cmd, '-t' + sep, 'plugin-info', ])[1]


def test_plugin_list(cap, system_id):
    out = call([cmd, 'list', '--type', 'PLUGINS'])[1]
    out = call([cmd, '-t' + sep, 'list', '--type', 'PLUGINS'])[1]


def test_error_paths(cap, system_id):

    # Generate bad argument exception
    call([cmd, 'list', '--type', 'SNAPSHOTS'], 2)
    call([cmd, 'list', '--type', 'SNAPSHOTS', '--fs', 'DOES_NOT_EXIST'], 2)


def create_all(cap, system_id):
    test_plugin_info(cap, system_id)
    test_block_creation(cap, system_id)
    test_fs_creation(cap, system_id)


def run_all_tests(cap, system_id):
    test_display(cap, system_id)
    test_plugin_list(cap, system_id)

    test_error_paths(cap, system_id)
    create_all(cap, system_id)

    test_mapping(cap, system_id)


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-c", "--command", action="store", type="string",
                      dest="cmd", help="specific command line to test")
    parser.add_option("-p", "--pool", action="store", dest="pool_name",
                      default='lsm_test_aggr',
                      help="pool name to use for testing")

    parser.add_option("-f", "--fspool", action="store", dest="fs_pool_id",
                      default='',
                      help="fs pool id to use for testing")

    parser.description = "lsmcli command line test tool"

    (options, args) = parser.parse_args()

    if options.cmd is None:
        print 'Please specify which lsmcli to test using -c or --command'
        sys.exit(1)
    else:
        cmd = options.cmd
        test_pool_name = options.pool_name

        if options.fs_pool_id:
            test_fs_pool_id = options.fs_pool_id

    #Theory of testing.
    # For each system that is available to us:
    #   Query capabilities
    #       Query all supported query operations (should have more to query)
    #
    #       Create objects of every supported type
    #           Query all supported query operations
    #           (should have more to query),
    #           run though different options making sure nothing explodes!
    #
    #       Try calling un-supported operations and expect them to fail
    systems = get_systems()

    for system in systems:
        c = capabilities(system[ID])
        run_all_tests(c, system[ID])
