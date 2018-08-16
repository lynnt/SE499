"""
To run this extension, the python name has to be as same as one of the loaded library
Additionally, the file must exist in a folder which is in gdb's safe path
"""
import collections
import gdb

# set these signal handlers with some settings (nostop, noprint, pass)
gdb.execute('handle SIGALRM nostop noprint pass')
gdb.execute('handle SIGUSR1 nostop noprint pass')

# GDB types for various structures/types in uC++
uCluster_ptr_type = gdb.lookup_type('uCluster').pointer()
uClusterDL_ptr_type = gdb.lookup_type('uClusterDL').pointer()
uBaseTask_ptr_type = gdb.lookup_type('uBaseTask').pointer()
uBaseTaskDL_ptr_type = gdb.lookup_type('uBaseTaskDL').pointer()
int_ptr_type = gdb.lookup_type('int').pointer()

# A named tuple representing information about a stack
StackInfo = collections.namedtuple('StackInfo', 'sp fp pc')

# A global variable to keep track of stack information as one context switches
# from one task to another task
STACK = []

def get_addr(addr):
    """
    NOTE: sketchy solution to retrieve address. There is a better solution...
    @addr: str of an address that can be in a format 0xfffff <type of the object
    at this address>
    Return: str of just the address
    """
    str_addr = str(addr)
    ending_addr_index = str_addr.find('<')
    if ending_addr_index == -1:
        return str(addr)
    return str_addr[:ending_addr_index].strip()

def print_usage(msg):
    """
    Print out usage message
    @msg: str
    """
    print('Usage: ' + msg)

def get_argv_list(args):
    """
    Split the argument list in string format, where each argument is separated
    by whitespace delimiter, to a list of arguments like argv
    @args: str of arguments
    Return:
        [] if args is an empty string
        list if args is not empty
    """
    # parse the string format of arguments and return a list of arguments
    argv = args.split(' ')
    if len(argv) == 1 and argv[0] == '':
        return []
    return argv

def get_cluster_root():
    """
    Return: gdb.Value of globalClusters.root (is an address)
    """
    cluster_root = gdb.parse_and_eval('uKernelModule::globalClusters.root')
    if cluster_root is None:
        print('uKernelModule::globalClusters list is None')
    return cluster_root

def lookup_cluster_by_name(cluster_name):
    """
    Look up a cluster given its ID
    @cluster_name: str
    Return: gdb.Value
    """
    cluster_root = get_cluster_root()
    if not cluster_root:
        print('Cannot get the root of the linked list of clusters')
        return
    cluster = None
    # need to keep track of the count to be able to tell if there are many tasks
    # with the same name
    cluster_count = 0

    # lookup for the task associated with the id
    if cluster_root['cluster_']['name'].string() == cluster_name:
        cluster = cluster_root['cluster_'].address
    else:
        curr = cluster_root
        while True:
            curr = curr['next'].cast(uClusterDL_ptr_type)

            if curr['cluster_']['name'].string() == cluster_name:
                cluster = curr['cluster_'].address
                break

            if curr == cluster_root:
                break

    if not cluster:
        print(
                ("Cannot find a cluster with the name: {}.".format(cluster_name))
             )
    return cluster

############################COMMAND IMPLEMENTATION#########################
class Clusters(gdb.Command):
    """Print out the list of available clusters"""
    def __init__(self):
        super(Clusters, self).__init__('clusters', gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        """
        Iterate through a circular linked list of clusters and print out its
        name along with address associated to each cluster
        @arg: str
        @from_tty: bool
        """

        cluster_root = get_cluster_root()
        if not cluster_root:
            print('Cannot get the root of the linked list of clusters')
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

class ClusterProcessors(gdb.Command):
    """Display a list of all info about all available processors on a particular
    cluster"""
    usage_msg = 'processors <cluster_name>'
    def __init__(self):
        super(ClusterProcessors, self).__init__('processors', gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        """
        Iterate through a circular linked list of tasks and print out all
        info about each processor in that cluster
        @arg: str
        @from_tty: bool
        """
        argv = get_argv_list(arg)
        if len(argv) != 1:
            print_usage(self.usage_msg)
            return

        cluster_address = lookup_cluster_by_name(argv[0])

        processor_root = (
            cluster_address.cast(uCluster_ptr_type)['processorsOnCluster']['root']
            )

        if processor_root is None:
            print('There is no processor for cluster at address: \
                    {}'.format(cluster_address))
            return

        uProcessorDL_ptr_type = gdb.lookup_type('uProcessorDL').pointer()
        print('{:>18}{:>20}{:>20}{:>20}'.format('Address', 'PID', 'Preemption',
            'Spin'))
        curr = processor_root

        while True:
            processor = curr['processor_']
            print(
                    ('{:>18}{:>20}{:>20}{:>20}'.format(get_addr(processor.address),
                        str(processor['pid']), str(processor['preemption']),
                        str(processor['spin']))
                )
            )

            curr = curr['next'].cast(uProcessorDL_ptr_type)
            if curr == processor_root:
                break

class Task(gdb.Command):
    """
    task                            : print all the tasks in a program
    task <task_address>             : context switch to a different task at address @task_address
    task <clusterName>              : print all the tasks in @clusterName
    task <clusterName> <task_id>    : context switch to a different task with an id
                                      @task_id and in cluster @clusterName
    """

    usage_msg = """
    task                            : print all the tasks in a program
    task <task_address>             : context switch to a different task at address @task_address
    task <clusterName>              : print all the tasks in @clusterName
    task <clusterName> <task_id>    : context switch to a different task with an id
                                      @task_id and in cluster @clusterName
    """
    def __init__(self):
        # The first parameter of the line below is the name of the command. You
        # can call it 'uc++ task'
        super(Task, self).__init__('task', gdb.COMMAND_USER)

    ############################AUXILIARY FUNCTIONS#########################

    def print_tasks_by_cluster_instance(self, cluster_address):
        """
        Display a list of all info about all available tasks on a particular
        cluster
        @cluster_address: gdb.Value
        """
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

    def print_tasks_by_cluster_address(self, cluster_address):
        """
        Display a list of all info about all available tasks on a particular
        cluster
        @cluster_address: str
        """
        # Iterate through a circular linked list of tasks and print out its
        # name along with address associated to each cluster

        # convert hex string to hex number
        try:
            hex_addr = int(cluster_address, 16)
        except:
            print_usage(self.usage_msg)
            return

        cluster_address = gdb.Value(hex_addr)
        self.print_tasks_by_cluster_instance(cluster_address)

    ############################COMMAND FUNCTIONS#########################
    def print_all_tasks(self):
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

            self.print_tasks_by_cluster_address(addr)
            curr = curr['next'].cast(uClusterDL_ptr_type)
            if curr == cluster_root:
                break

    def pushtask_by_address(self, task_address):
        """Change to a new task by switching to a different stack and manually
        adjusting sp, fp and pc
        @task_address: str
            2 supported format:
                in hex format
                    <hex_address>: literal hexadecimal address
                    Ex: 0xffffff
                in name of the pointer to the task
                    "task_name": pointer of the variable name of the cluster
                        Ex: T* s -> task_name = s
            Return: gdb.value of the cluster's address
        """
        # Task address has a format "task_address", which implies that it is the
        # name of the variable, and it needs to be evaluated
        if task_address.startswith('"') and task_address.endswith('"'):
            task = gdb.parse_and_eval(task_address.replace('"', ''))
        else:
        # Task address format does not include the quotation marks, which implies
        # that it is a hex address
            # convert hex string to hex number
            try:
                hex_addr = int(task_address, 16)
            except:
                print_usage(self.usage_msg)
                return
            task_address = gdb.Value(hex_addr)
            task = task_address.cast(uBaseTask_ptr_type)

        uContext_t_ptr_type = gdb.lookup_type('UPP::uMachContext::uContext_t').pointer()

        task_state = task['state']

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
        xpc = get_addr(gdb.parse_and_eval('uSwitch').address + 28)

        # must be at frame 0 to set pc register
        gdb.execute('select-frame 0')

        # push sp, fp, pc into a global stack
        global STACK
        sp = gdb.parse_and_eval('$sp')
        fp = gdb.parse_and_eval('$fp')
        pc = gdb.parse_and_eval('$pc')
        stack_info = StackInfo(sp = sp, fp = fp, pc = pc)
        STACK.append(stack_info)

        # updater registers for new task
        gdb.execute('set $rsp={}'.format(xsp))
        gdb.execute('set $rbp={}'.format(xfp))
        gdb.execute('set $pc={}'.format(xpc))

    def pushtask_by_id(self, cluster_name, task_id):
        """
        @cluster_name: str
        @task_id: str
        """
        try:
            task_id = int(task_id)
        except:
            print_usage(self.usage_msg)
            return

        # retrieve the address associated with the cluster name
        cluster_address = lookup_cluster_by_name(cluster_name)
        if not cluster_address:
            return

        task_root = (
            cluster_address.cast(uCluster_ptr_type)['tasksOnCluster']['root']
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
            self.pushtask_by_address(task_addr)

    def print_tasks_by_cluster_name(self, cluster_name):
        """
        Print out all the tasks available in the cluster with name @cluster_name
        @cluster_name: str
        """
        cluster_address = lookup_cluster_by_name(cluster_name)
        if not cluster_address:
            return

        self.print_tasks_by_cluster_instance(cluster_address)

    def invoke(self, arg, from_tty):
        """
        @arg: str
        @from_tty: bool
        """
        argv = get_argv_list(arg)
        if len(argv) == 0:
            self.print_all_tasks()
        elif len(argv) == 1:
            # pushtask with an address
            if argv[0].startswith('0x') or argv[0].startswith('"'):
                self.pushtask_by_address(argv[0])
            else:
                self.print_tasks_by_cluster_name(argv[0])
        elif len(argv) == 2:
            self.pushtask_by_id(argv[0], argv[1])
        else:
            print_usage(self.usage_msg)

class PopTask(gdb.Command):
    """Switch back to previous task on the stack"""
    usage_msg = 'poptask <task_address>'

    def __init__(self):
        super(PopTask, self).__init__('poptask', gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        """
        @arg: str
        @from_tty: bool
        """
        global STACK
        if len(STACK) != 0:
            # must be at frame 0 to set pc register
            gdb.execute('select-frame 0')

            # pop stack
            stack_info = STACK.pop()
            pc = get_addr(stack_info.pc)
            sp = stack_info.sp
            fp = stack_info.fp

            # pop sp, fp, pc from global stack
            gdb.execute('set $pc = {}'.format(pc))
            gdb.execute('set $rbp = {}'.format(fp))
            gdb.execute('set $sp = {}'.format(sp))

            # must be at C++ frame to access C++ vars
            gdb.execute('frame 1')
        else:
            print('empty stack')

class ResetOriginFrame(gdb.Command):
    """Reset to the origin frame prior to continue execution again"""
    usage_msg = 'resetOriginFrame'
    def __init__(self):
        super(ResetOriginFrame, self).__init__('reset', gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        """
        @arg: str
        @from_tty: bool
        """
        global STACK
        stack_info = STACK.pop(0)
        STACK.clear()
        pc = get_addr(stack_info.pc)
        sp = stack_info.sp
        fp = stack_info.fp

        # pop sp, fp, pc from global stack
        gdb.execute('set $pc = {}'.format(pc))
        gdb.execute('set $rbp = {}'.format(fp))
        gdb.execute('set $sp = {}'.format(sp))

        # must be at C++ frame to access C++ vars
        gdb.execute('frame 1')

Clusters()
ClusterProcessors()
PopTask()
ResetOriginFrame()
Task()
