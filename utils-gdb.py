"""
To run this extension, the python name has to be as same as one of the loaded library
Additionally, the file must exist in a folder which is in gdb's safe path
"""
import gdb

# set these signal handlers with some settings (nostop, noprint, pass)
gdb.execute('handle SIGALRM nostop noprint pass')
gdb.execute('handle SIGUSR1 nostop noprint pass')

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
        print('{:>20}\t{}'.format('Name', 'Address'))

        while True:
            print(
                ('{:>20}\t{}'.format(curr['cluster_']['name'].string(),
                                     curr['cluster_'].reference_value()))
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
        if len(arg) < 1:
            print('Usage: cluster_tasks <cluster_address>')

        # convert to hex string to hex number
        hex_addr = int(arg, 16)
        uCluster_ptr_type = gdb.lookup_type('uCluster').pointer()
        uBaseTaskDL_ptr_type = gdb.lookup_type('uBaseTaskDL').pointer()
        cluster_address = gdb.Value(hex_addr)

        task_root = (
            cluster_address.cast(uCluster_ptr_type)['tasksOnCluster']['root']
            )

        if task_root is None:
            print('There is no tasks for cluster at address: \
                    {}'.format(cluster_address))
            return

        curr = task_root
        while True:
            print(
                ('{:>20}\t{}\t{}'.format(curr['task_']['name'].string(),
                                         curr['task_'].reference_value(),
                                         curr['task_']['state'])
                )
            )

            curr = curr['next'].cast(uBaseTaskDL_ptr_type)
            if curr == task_root:
                break

Clusters()
ClusterTasks()
