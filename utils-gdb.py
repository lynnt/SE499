"""
To run this extension, the python name has to be as same as one of the loaded library
Additionally, the file must exist in a folder which is in gdb's safe path
"""
import gdb

# set these signal handlers with some settings (nostop, noprint, pass)
gdb.execute('handle SIGALRM nostop noprint pass')
gdb.execute('handle SIGUSR1 nostop noprint pass')

STACK = 0

class Clusters(gdb.Command):
    """Print out the list of available clusters"""
    def __init__(self):
        super(Clusters, self).__init__('clusters', gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        """Iterate through a circular linked list of clusters and print out its
        name along with address associated to each cluster"""

        uClusterDL_ptr_type = gdb.lookup_type('uClusterDL').pointer()
        cluster_root = gdb.parse_and_eval('uKernelModule::globalClusters.root')
        if cluster_root is None:
            print('uKernelModule::globalClusters list is None')
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

class ClusterTasks(gdb.Command):
    """Display a list of all info about all available tasks on a particular
    cluster"""
    def __init__(self):
        super(ClusterTasks, self).__init__('cluster_tasks', gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        """Iterate through a circular linked list of tasks and print out its
        name along with address associated to each cluster"""
        if not arg:
            print('Usage: cluster_tasks <cluster_address>')
            return

        # convert to hex string to hex number
        uCluster_ptr_type = gdb.lookup_type('uCluster').pointer()
        uBaseTaskDL_ptr_type = gdb.lookup_type('uBaseTaskDL').pointer()
        hex_addr = int(arg, 16)
        cluster_address = gdb.Value(hex_addr)

        task_root = (
            cluster_address.cast(uCluster_ptr_type)['tasksOnCluster']['root']
            )

        if task_root is None:
            print('There is no tasks for cluster at address: \
                    {}'.format(cluster_address))
            return

        print('{:>20}{:>18}{:>25}'.format('Task Name', 'Address', 'State'))
        curr = task_root
        while True:
            print(
                    ('{:>20}{:>18}{:>25}'.format(curr['task_']['name'].string(),
                    str(curr['task_'].reference_value())[1:],
                    str(curr['task_']['state']))
                )
            )

            curr = curr['next'].cast(uBaseTaskDL_ptr_type)
            if curr == task_root:
                break

class Tasks(gdb.Command):
    """List all the tasks' info for all available clusters"""
    def __init__(self):
        super(Tasks, self).__init__('tasks', gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        """Iterate through each cluster, iterate through all tasks and  print out info about all the tasks
        in those clusters"""
        uClusterDL_ptr_type = gdb.lookup_type('uClusterDL').pointer()
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
    """Switch to a different task"""
    def __init__(self):
        super(PushTask, self).__init__('push_task', gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        """Change to a new task by switching to a different stack and manually
        adjusting sp, fp and pc"""
        if not arg:
            print('Usage: push_task <task_address>')
            return

        # convert to hex string to hex number
        hex_addr = int(arg, 16)
        uBaseTask_ptr_type = gdb.lookup_type('uBaseTask').pointer()
        uContext_t_ptr_type = gdb.lookup_type('UPP::uMachContext::uContext_t').pointer()
        task_address = gdb.Value(hex_addr)

        task_context = (
            task_address.cast(uBaseTask_ptr_type)['context'].cast(uContext_t_ptr_type)
            )

        xsp = task_context['SP'] + 48
        xfp = task_context['FP']
        if not gdb.lookup_symbol('uSwitch'):
            print('uSwitch symbol is not available')
            return

        # convert to string so we can strip out the address
        xpc = str(gdb.parse_and_eval('uSwitch').address + 28)
        # address is followed by type with format: addr <type>
        ending_addr_index = xpc.find('<')
        if ending_addr_index == -1:
            print("Can't get PC address in correct format")
            return

        xpc = xpc[:ending_addr_index].strip()

        # update the level of stack
        global STACK
        STACK += 1

        # must be at frame 0 to set pc register
        gdb.execute('select-frame 0')
        # push sp, fp, pc into global variables

        gdb.execute('set $__sp{} = $sp'.format(STACK))
        gdb.execute('set $__fp{} = $sp'.format(STACK))
        gdb.execute('set $__pc{} = $sp'.format(STACK))

        # updater registers for new task
        gdb.execute('set $rsp={}'.format(xsp))
        gdb.execute('set $rbp={}'.format(xfp))
        gdb.execute('set $pc={}'.format(xpc))
        gdb.execute('frame 1')

Clusters()
ClusterTasks()
PushTask()
Tasks()
