import epics
import subprocess
import time
#NOTE: this script must only launch from xspress3 host computer
def restart_ioc():
    subprocess.run([xspress3_launch_cmd, "restart"])

#checking xspress3 responsive during scan 
prefix = "8bmbsft:"
xp3 = "8bmbXP3:"
struck = "8bmb:3820:"
xp3_setup_calc = "8bmbsft:userTran14.PROC"
xspress3_launch_cmd = "/net/s8bmdserv/xorApps/epics/synApps_6_3/ioc/8bmbxspress3/iocBoot/iocbmb_8ChXspress3/softioc/8bmb_8ChXspress3.pl"

epics.caput(f"{prefix}timer1:Go", 1)

terminate_flag = False
attempt_fix_flag = False
scanning_flag = epics.caget(f"{prefix}Fbefore1.VAL")

while scanning_flag: 
    fly_scanning = epics.caget(f"{prefix}Fbefore1.VAL")
    fly_pause = epics.caget(f"{prefix}FscanPause.VAL")
    fly_wait = epics.caget(f"{prefix}Fscan1.WCNT")

    step_scanning = epics.caget(f"{prefix}before2.VAL")
    step_pause = epics.caget(f"{prefix}scan2Pause.VAL")
    step_wait = epics.caget(f"{prefix}scan2.WCNT")

    xp3_acquiring = epics.caget(f"{xp3}det1:DetectorState_RBV")
    xp3_rate = epics.caget(f"{xp3}det1:ArrayRate_RBV")

    struck_acquiring = epics.caget(f"{struck}Acquiring")
    struck_current_channel = epics.caget(f"{struck}CurrentChannel")
    struck_requested_channel = epics.caget(f"{struck}NuseAll")
    timer_time = epics.caget(f"{prefix}timer1:elapsedSecs")

    if fly_scanning and not fly_pause and fly_wait == 0 and xp3_acquiring == 1 and xp3_rate > 0:
            epics.caput(f"{prefix}timer1:Go", 1)
            attempt_fix_flag = 0

    elif step_scanning and not step_pause and step_wait == 0 and xp3_acquiring == 1 and xp3_rate > 0:
        epics.caput(f"{prefix}timer2:Go", 1)
        attempt_fix_flag = 0

    elif fly_scanning and not fly_pause and fly_wait == 0 and xp3_acquiring == 1 and xp3_rate == 0 and \
        timer_time > 10 and struck_acquiring == 0 and struck_current_channel == struck_requested_channel:
            if not attempt_fix_flag:
                epics.caput(f"{xp3}:HDF1:Capture", 0)
                epics.caput(f"{struck}Acquire", 0)
                epics.caput(f"{prefix}timer1:Go", 1)
                attempt_fix_flag=True
            else: #subprocess
                epics.caget(f"{prefix}Fscan1.WAIT", 1)
                restart_ioc()
                time.sleep(5)
                epics.caput(xp3_setup_calc, 1)
                current_line = epics.caget(f"{prefix}Fscan1.CPT")+1
                epics.caput(f"{xp3}HDF1:FileNumber", current_line)
                epics.caget(f"{prefix}Fscan1.WAIT", 0)

    time.sleep(1)          
    scanning_flag = epics.caget(f"{prefix}Fbefore1.VAL")

#after scan: stop xspress3 monitor.py 
epics.caput(f"{prefix}timer1:Go", 1)
epics.caput(f"{prefix}timer2:Go", 0)
