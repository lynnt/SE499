handle SIGALRM nostop noprint pass
handle SIGUSR1 nostop noprint pass
set var $stack = 0

define clusters
        set var $croot = (uClusterDL *)uKernelModule::globalClusters.root
        set var $ccurr = $croot
        printf "%-20s %-18s\n", "name", "address"
        while 1
            printf "%-20s %18p\n", $ccurr.cluster_.name, &$ccurr.cluster_
            set var $ccurr = (uClusterDL *)$ccurr.next
            if $ccurr == $croot
                loop_break
                end
        end
end

define cluster_tasks
        set var $troot = (uBaseTaskDL *)((uCluster *)$arg0)->tasksOnCluster.root
        if $troot != 0
            set var $tcurr = $troot
            printf "%-20s %-18s %-20s\n", "name", "address", "state"
            while 1
                printf "%-20s %18p ", $tcurr.task_.name, &$tcurr.task_
                output $tcurr.task_.state
                echo \n
                set var $tcurr = (uBaseTaskDL *)$tcurr.next
                if $tcurr == $troot
                    loop_break
                    end
            end
        else
            printf "no tasks"
        end
end

define cluster_procs
        set var $proot = (uProcessorDL *)((uCluster *)$arg0)->processorsOnCluster.root
        if $proot != 0
                set var $pcurr = $proot
                printf "%-18s %-20s %-20s %-20s\n", "address", "pid", "preemption", "spin"
                while 1
                        printf "%18p %-20d %-20d %-20d\n", &$pcurr.processor_, $pcurr.processor_.pid, $pcurr.processor_.preemption, $pcurr.processor_.spin
                        set var $pcurr = (uProcessorDL *)$pcurr.next
                    if $pcurr == $proot
                                loop_break
                                end
                end
        else
                printf "no processors"
        end
end

define tasks
        set var $croot = (uClusterDL *)uKernelModule::globalClusters.root
        set var $ccurr = $croot
        while 1
                printf "%-20s %18p\n", $ccurr.cluster_.name, &$ccurr.cluster_
                cluster_tasks &$ccurr.cluster_
                echo \n
                set var $ccurr = (uClusterDL *)$ccurr.next
            if $ccurr == $croot
                        loop_break
                        end
        end
end

define events
        set var $eroot = uProcessor::events.eventlist.root
        if $eroot != 0
                set var $ecurr = $eroot
                printf "%-18s %-20s %-20s %-18s %-20s %-18s %-20s\n", "address", "alarm", "period", "task", "name", "handler", "locked"
                while 1
                        printf "%18p %20lld %20lld %18p %-20s %18p %20d\n", $ecurr, $ecurr.alarm.tv, $ecurr.period.tv, $ecurr.task, $ecurr.task.name, $ecurr.sigHandler, $ecurr.executeLocked
                        set var $ecurr = (uEventNode *)$ecurr.next
                    if $ecurr == $eroot
                                loop_break
                                end
                end
        else
                printf "no events"
        end
end

define walk-386
        set var $xsp = ((void ***)((uBaseTask *)$arg0)->context)[1]
        p $xsp
        set var $xip = ((void **)((uBaseTask *)$arg0)->context)[2]
        output/a $xip
        set var $nsp = *(void ***)($xsp)
        while $nsp != 0
                set var $xip = *(void **)($xsp+1)
                printf " ( "
                set var $i = 2
                while $i < 10
                        printf "0x%x ", *(void **)($xsp + $i)
                        set var $i += 1
                end
                printf ")\n"
                output/a $xip
                set var $xsp = $nsp
                set var $nsp = *(void ***)($xsp)
        end
        printf "\n"
end

define apply-cluster-tasks
        set var $troot = (uBaseTaskDL *)((uCluster *)$arg0)->tasksOnCluster.root
        set var $tcurr = $troot
        printf "0x%18p %-20s ", &$tcurr.task_, $tcurr.task_.name
        output $tcurr.task_.state
        echo \n
        $arg1 &$tcurr.task_
        set var $tcurr = (uBaseTaskDL *)$tcurr.next
        while $tcurr != $troot
                printf "0x%18p %-20s ", &$tcurr.task_, $tcurr.task_.name
                output $tcurr.task_.state
                echo \n
                $arg1 &$tcurr.task_
                set var $tcurr = (uBaseTaskDL *)$tcurr.next
        end
end

define apply-cluster-ready-tasks
        set var $troot = (uBaseTaskDL *)((uCluster *)$arg0)->tasksOnCluster.root
        set var $tcurr = $troot
        if $tcurr.task_.state == uBaseTask::Ready
                printf "0x%18p %-20s ", &$tcurr.task_, $tcurr.task_.name
                output $tcurr.task_.state
                echo \n
        end
        $arg1 &$tcurr.task_
        set var $tcurr = (uBaseTaskDL *)$tcurr.next
        while $tcurr != $troot
                if $tcurr.task_.state == uBaseTask::Ready
                        printf "0x%18p %-20s ", &$tcurr.task_, $tcurr.task_.name
                        output $tcurr.task_.state
                        echo \n
                        $arg1 &$tcurr.task_
                end
                set var $tcurr = (uBaseTaskDL *)$tcurr.next
        end
end

define walk-386-stack
        set var $xsp = $arg0
        set var $nsp = *(void ***)($xsp)
        while $nsp != 0
                set var $xip =  *(void **)($xsp+1)
                printf " ( "
                set var $i = 2
                while $i < 10
                        printf "0x%x ", *(void **)($xsp + $i)
                        set var $i += 1
                end
                printf ")\n"
                output/a $xip
                set var $xsp = $nsp
                set var $nsp = *(void ***)($xsp)
        end
        printf "\n"
end

define pushtask
        printf "Switching stack .... \n"
        # push stack
        set $stack++
        # set values while on a C++ stack frame
        set var $xsp = (*(UPP::uMachContext::uContext_t *)((uBaseTask *)$arg0)->context).SP+48
        set var $xfp = (*(UPP::uMachContext::uContext_t *)((uBaseTask *)$arg0)->context).FP
        set var $xpc = uSwitch+28
        # must be at frame 0 to set pc register, now on assembler frame
        frame 0
        # push sp, fp, pc into global variables
        printf "Push sp, fp, pc into global variables\n"
        eval "set $__sp%d = $sp", $stack
        eval "set $__fp%d = $fp", $stack
        eval "set $__pc%d = $pc", $stack
        # now update registers for new task
        printf "Update registers for new task\n"
        set $rsp = $xsp
        set $rbp = $xfp
        set $pc = $xpc
        # must be at C++ frame to access C++ variables (uSwitch is assembler)
        frame 1
end

define poptask
        if $stack != 0
                # must be at frame 0 to set pc register
                select-frame 0
                # pop sp, fp, pc from global variables
                eval "set $pc = $__pc%d", $stack
                eval "set $rbp = $__fp%d", $stack
                eval "set $sp = $__sp%d", $stack
                # pop stack
                set $stack--
                # must be at C++ frame to access C++ variables (uSwitch is assembler)
                frame 1
        else
                printf "empty stack\n"
        end
end
