import gdb

gdb.execute('handle SIGALRM nostop noprint pass')
gdb.execute('handle SIGUSR1 nostop noprint pass')

class Clusters(gdb.Command):
    """Print out the list of available clusters"""
    def __init__(self):
        super(Clusters, self).__init__('clusters', gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        uCluster_type = gdb.lookup_type('uClusterDL').pointer()
        cluster_root = gdb.parse_and_eval('uKernelModule::globalClusters.root')
        curr = cluster_root
        print('{:>20}\t{}'.format('Name', 'Address'))
        while True:
            print('{:>20}\t{}'.format(curr['cluster_']['name'].string(), \
                curr['cluster_'].reference_value()))
            curr = curr['next'].cast(uCluster_type)
            if curr == cluster_root:
                break

Clusters()
