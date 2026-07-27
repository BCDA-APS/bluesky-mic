import os

def light_switch(direction):
    if direction=='Up' or direction==1:
        os.system('echo Trigger Up | nc 10.54.120.96 5000')
        pass
    elif direction=='Down' or direction==0:
        os.system('echo Trigger Down | nc 10.54.120.96 5000')
        pass
