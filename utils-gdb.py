"""
To run this extension, the python name has to be as same as one of the loaded library
Additionally, the file must exist in a folder which is in gdb's safe path
"""
import gdb

# set these signal handlers with some settings (nostop, noprint, pass)
gdb.execute('handle SIGALRM nostop noprint pass')
gdb.execute('handle SIGUSR1 nostop noprint pass')

STACK = 0
uCluster_ptr_type = gdb.lookup_type('uCluster').pointer()
uClusterDL_ptr_type = gdb.lookup_type('uClusterDL').pointer()
uBaseTask_ptr_type = gdb.lookup_type('uBaseTask').pointer()
uBaseTaskDL_ptr_type = gdb.lookup_type('uBaseTaskDL').pointer()

def print_usage(msg):
    print('Usage: ' + msg)

def get_cluster_root():
    cluster_root = gdb.parse_and_eval('uKernelModule::globalClusters.root')
    if cluster_root is None:
        print('uKernelModule::globalClusters list is None')
    return cluster_root

class Clusters(gdb.Command):
    """Print out the list of available clusters"""
    def __init__(self):
        super(Clusters, self).__init__('clusters', gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        """Iterate through a circular linked list of clusters and print out its
        name along with address associated to each cluster"""

        cluster_root = get_cluster_root()
        if not cluster_root:
            return
        curr = cluster_root
        print('{:>20}{:>18}'.format('Name', 'Address'))

        while True:
            print(
                    ('{:>20}{:>18}'.format(curr['cluster_']['name'].string(),
                        str(curr['cluster_'].reference_value())[1:]))
                )
            curr = curr['next'].cast(uClusterDL_ptr_type)
            if curr == cluster_root:
                break

class ClusterProcs(gdb.Command):
    """Display a list of all info about all available processors on a particular
    cluster"""
    usage_msg = 'cluster_procs <cluster_address>'
    def __init__(self):
        super(ClusterProcs, self).__init__('cluster_procs', gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        """Iterate through a circular linked list of tasks and print out all
        info about each processor in that cluster"""
        if not arg:
            print_usage(self.usage_msg)
            return

        # convert hex string to hex number
        try:
            hex_addr = int(arg, 16)
        except:
            print_usage(self.usage_msg)
            return

        cluster_address = gdb.Value(hex_addr)

        proc_root = (
            cluster_address.cast(uCluster_ptr_type)['processorsOnCluster']['root']
            )

        if proc_root is None:
            print('There is no processor for cluster at address: \
                    {}'.format(cluster_address))
            return

        uProcessorDL_ptr_type = gdb.lookup_type('uProcessorDL').pointer()
        print('{:>18}{:>20}{:>20}{:>20}'.format('Address', 'PID', 'Preemption',
            'Spin'))
        curr = proc_root

        while True:
            processor = curr['processor_']
            print(
                    ('{:>18}{:>20}{:>20}{:>20}'.format(str(processor.address),
                        str(processor['pid']), str(processor['preemption']),
                        str(processor['spin']))
                )
            )

            curr = curr['next'].cast(uProcessorDL_ptr_type)
            if curr == proc_root:
                break

class ClusterTasks(gdb.Command):
    """Display a list of all info about all available tasks on a particular
    cluster"""
    usage_msg = 'cluster_tasks <cluster_address>'
    def __init__(self):
        super(ClusterTasks, self).__init__('cluster_tasks', gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        """Iterate through a circular linked list of tasks and print out its
        name along with address associated to each cluster"""
        if not arg:
            print_usage(self.usage_msg)
            return

        # convert hex string to hex number
        try:
            hex_addr = int(arg, 16)
        except:
            print_usage(self.usage_msg)
            return

        cluster_address = gdb.Value(hex_addr)

        task_root = (
            cluster_address.cast(uCluster_ptr_type)['tasksOnCluster']['root']
            )

        if task_root is None:
            print('There is no tasks for cluster at address: \
                    {}'.format(cluster_address))
            return

        print('{:>4}{:>20}{:>18}{:>25}'.format('ID', 'Task Name', 'Address', 'State'))
        curr = task_root
        task_id = 0

        while True:
            print(
                    ('{:>4}{:>20}{:>18}{:>25}'.format(task_id, curr['task_']['name'].string(),
                    str(curr['task_'].reference_value())[1:],
                    str(curr['task_']['state']))
                )
            )

            curr = curr['next'].cast(uBaseTaskDL_ptr_type)
            task_id += 1
            if curr == task_root:
                break

class Tasks(gdb.Command):
    """List all the tasks' info for all available clusters"""
    def __init__(self):
        super(Tasks, self).__init__('tasks', gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        """Iterate through each cluster, iterate through all tasks and  print out info about all the tasks
        in those clusters"""
        cluster_root = gdb.parse_and_eval('uKernelModule::globalClusters.root')
        if cluster_root is None:
            print('uKernelModule::globalClusters list is None')
            return

        curr = cluster_root
        print('{:>20}{:>18}'.format('Cluster Name', 'Address'))

        while True:
            addr = str(curr['cluster_'].reference_value())[1:]
            print(
                    ('{:>20}{:>18}'.format(curr['cluster_']['name'].string(),
                        addr))
                )

            ClusterTasks().invoke(addr, False)
            curr = curr['next'].cast(uClusterDL_ptr_type)
            if curr == cluster_root:
                break

class PushTask(gdb.Command):
    """Switch to a different task using task's address"""
    usage_msg = 'pushtask <task_address>'

    def __init__(self):
        super(PushTask, self).__init__('pushtask', gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        """Change to a new task by switching to a different stack and manually
        adjusting sp, fp and pc"""
        if not arg:
            print_usage(self.usage_msg)
            return

        args = arg.split(' ')
        if len(args) > 1:
            print_usage(self.usage_msg)
            return

        # update the level of stack
        global STACK
        STACK += 1

        # convert hex string to hex number
        try:
            hex_addr = int(arg, 16)
        except:
            print_usage(self.usage_msg)
            return

        uContext_t_ptr_type = gdb.lookup_type('UPP::uMachContext::uContext_t').pointer()
        task_address = gdb.Value(hex_addr)

        task = task_address.cast(uBaseTask_ptr_type)
        task_state = (
            str(task_address.cast(uBaseTask_ptr_type)['state']).split('::', 1)[-1]
        )

        if task_state == 'Terminate':
            print('Cannot switch to a terminated thread')
            return

        task_context = task['context'].cast(uContext_t_ptr_type)

        # lookup for sp,fp and uSwitch
        xsp = task_context['SP'] + 48
        xfp = task_context['FP']
        if not gdb.lookup_symbol('uSwitch'):
            print('uSwitch symbol is not available')
            return

        # convert string so we can strip out the address
        xpc = str(gdb.parse_and_eval('uSwitch').address + 28)

        # address is followed by type with format: addr <type>
        ending_addr_index = xpc.find('<')
        if ending_addr_index == -1:
            print("Can't get PC address in correct format")
            return

        xpc = xpc[:ending_addr_index].strip()

        # must be at frame 0 to set pc register
        gdb.execute('select-frame 0')

        # push sp, fp, pc into global variables
        gdb.execute('set $__sp{} = $sp'.format(STACK))
        gdb.execute('set $__fp{} = $fp'.format(STACK))
        gdb.execute('set $__pc{} = $pc'.format(STACK))

        # updater registers for new task
        gdb.execute('set $rsp={}'.format(xsp))
        gdb.execute('set $rbp={}'.format(xfp))
        gdb.execute('set $pc={}'.format(xpc))

class PopTask(gdb.Command):
    """Switch to back to previous task on the stack"""
    usage_msg = 'poptask <task_address>'

    def __init__(self):
        super(PopTask, self).__init__('poptask', gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        global STACK
        if STACK != 0:
            # must be at frame 0 to set pc register
            gdb.execute('select-frame 0')

            # pop sp, fp, pc from global vars
            gdb.execute('set $pc = $__pc{}'.format(STACK))
            gdb.execute('set $rbp = $__fp{}'.format(STACK))
            gdb.execute('set $sp = $__sp{}'.format(STACK))

            # pop stack
            STACK -= 1
            # must be at C++ frame to access C++ vars
            gdb.execute('frame 1')
        else:
            print('empty stack')

class PushTaskID(gdb.Command):
    """Switch to a different task using task id"""
    usage_msg = 'pushtask_id <task_id> [cluster_id]'
    def __init__(self):
        super(PushTaskID, self).__init__('pushtask_id', gdb.COMMAND_USER)

    def lookup_cluster(self, cluster_id):
        curr_id = 0

        cluster_root = get_cluster_root()
        if not cluster_root:
            return
        cluster = None

        # lookup for the task associated with the id
        if cluster_id == curr_id:
            cluster = cluster_root['cluster_'].address
        else:
            curr = cluster_root
            while True:
                curr = curr['next'].cast(uClusterDL_ptr_type)
                curr_id += 1

                if curr_id == cluster_id:
                    cluster = curr['cluster_'].address
                    break

                if curr == cluster_root:
                    break

        if curr_id < cluster_id:
            print(
                    ("Can't find cluster ID: {}. Only have {} clusters".format(cluster_id, curr_id))
                )
        return cluster

    def invoke(self, arg, from_tty):
        if not arg:
            print_usage(self.usage_msg)
            return

        args = arg.split(' ')
        try:
            task_id = int(args[0])
        except:
            print_usage(self.usage_msg)
            return

        cluster = None
        cluster_id = -1

        # cmd line argument parsing
        if len(args) == 1:
            cluster = gdb.parse_and_eval('&uThisCluster()')
        elif len(args) == 2:
            try:
               cluster_id = int(args[1])
            except:
                print_usage(self.usage_msg)
                return
        else:
            print_usage(self.usage_msg)
            return

        # check if cluster_id is within the appriopriate range and lookup for
        # the right cluster if asked
        if cluster_id > -1:
            cluster = self.lookup_cluster(cluster_id)
            if not cluster:
                return;
        elif cluster_id < -1:
            print('Unvalid range of cluster_id')
            return

        print('Cluster: ', cluster['name'].string())
        task_root = (
            cluster.cast(uCluster_ptr_type)['tasksOnCluster']['root']
            )

        if not task_root:
            print('tasksOnCluster list is None')
            return

        curr_id = 0
        task_addr = None

        # lookup for the task associated with the id
        if task_id == curr_id:
            task_addr = str(task_root['task_'].address)
        else:
            curr = task_root
            while True:
                curr = curr['next'].cast(uBaseTaskDL_ptr_type)
                curr_id += 1

                if curr_id == task_id:
                    task_addr = str(curr['task_'].address)
                    break

                if curr == task_root:
                    break

        if not task_addr:
            print(
                    ("Can't find task ID: {}. Only have {} tasks".format(task_id,curr_id))
                )
        else:
            PushTask().invoke(task_addr, False)

Clusters()
ClusterProcs()
ClusterTasks()
PopTask()
PushTask()
PushTaskID()
Tasks()
