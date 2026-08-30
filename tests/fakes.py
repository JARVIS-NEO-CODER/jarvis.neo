from core.system_observer import SystemSnapshot

class ControlledObserver:
    def __init__(self):
        self.index=0
        self.states=[("Desktop","explorer.exe"),("Test App","test.exe")]
    def snapshot(self):
        window, process=self.states[min(self.index,len(self.states)-1)]
        self.index+=1
        return SystemSnapshot(float(self.index),active_window=window,active_process=process)

class RecoveryPlanner:
    def plan(self, objective, manifest):
        return {"steps":[{"action":"test.first","kwargs":{},"description":"Controlled failure"}]}
    def replan(self, objective, manifest, **kwargs):
        return {"steps":[{"action":"test.recovery","kwargs":{},"description":"Controlled recovery"}]}
