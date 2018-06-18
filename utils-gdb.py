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
uBaseTask_ptr_type = gdb.lookup_type('uBaseTask').pointer()
uBaseTaskDL_ptr_type = gdb.lookup_type('uBaseTaskDL').pointer()

def print_usage(msg):
    print('Usage: ' + msg)

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
        hex_addr = int(arg, 16)
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

class PushTask(gdb.Command):
    """Switch to a different task using task's address"""
    def __init__(self):
        super(PushTask, self).__init__('pushtask', gdb.COMMAND_USER)
        self.usage_msg = 'pushtask <task_address>'

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

        # convert to hex string to hex number
        hex_addr = int(arg, 16)
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
        gdb.execute('frame 1')

class PopTask(gdb.Command):
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

#TODO: fixme
class PushTaskID(gdb.Command):
    def __init__(self):
        super(PushTaskID, self).__init__('pushtask_id', gdb.COMMAND_USER)
        self.usage_msg = 'pushtask_id <task_id> [cluster_address]'

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

        curr_cluster = None

        if len(args) == 1:
            curr_cluster = gdb.parse_and_eval('&uThisCluster()')
            print('Current cluster: ', curr_cluster['name'].string())
        #elif len(args) == 2:
        #    cluster_addr = args[1]
        else:
            print_usage(self.usage_msg)
            return

        task_root = (
            curr_cluster.cast(uCluster_ptr_type)['tasksOnCluster']['root']
            )

        if not task_root:
            print('tasksOnCluster list is None')
            return

        curr = task_root
        curr_id = 0
        task_addr = None

        while True:
            curr = curr['next'].cast(uBaseTaskDL_ptr_type)

            if curr == task_root:
                break

            if curr_id == task_id:
                task_addr = str(curr['task_'].address)
                break

            curr_id += 1

        if curr_id < task_id:
            print(
                    ("Can't find task ID: {}. Only have {} tasks".format(task_id,curr_id))
                )
        else:
            PushTask().invoke(task_addr, False)


Clusters()
ClusterTasks()
PopTask()
PushTask()
PushTaskID()
Tasks()
