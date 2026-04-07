import py_compile

path_vw = 'e:/projectnew/controller/voice_worker.py'
text = open(path_vw, 'rb').read().decode('utf-8')

# Fix 1: _handle_pending_voice_confirmation - after voice handles No,
# also close the popup dialog via a new signal so it doesn't double-fire
old_no = (
    '        if text in no_phrases:\n'
    '            with self._critical_lock:\n'
    '                self._pending_critical = None\n'
    '            self.action_logged.emit(f"VOICE: {pending[\'label\']} cancelled by voice.")\n'
    '            _say(f"Cancelled {pending[\'label\']}")\n'
    '            return True\n'
)
new_no = (
    '        if text in no_phrases:\n'
    '            with self._critical_lock:\n'
    '                self._pending_critical = None\n'
    '            self.action_logged.emit(f"VOICE: {pending[\'label\']} cancelled by voice.")\n'
    '            _say(f"Cancelled {pending[\'label\']}")\n'
    '            # Close popup without triggering set_critical_confirmation_result again\n'
    '            self.dismiss_confirm_dialog.emit()\n'
    '            return True\n'
)
assert old_no in text, "no_phrases block not found"
text = text.replace(old_no, new_no, 1)

# Fix 2: same for yes path - dismiss popup without double-executing
old_yes = (
    '        if text in yes_phrases:\n'
    '            with self._critical_lock:\n'
    '                self._pending_critical = None\n'
    '            self.action_logged.emit(f"VOICE: {pending[\'label\']} confirmed by voice.")\n'
    '            self._execute_critical_action(pending)\n'
    '            return True\n'
)
new_yes = (
    '        if text in yes_phrases:\n'
    '            with self._critical_lock:\n'
    '                self._pending_critical = None\n'
    '            self.action_logged.emit(f"VOICE: {pending[\'label\']} confirmed by voice.")\n'
    '            self._execute_critical_action(pending)\n'
    '            # Close popup without triggering set_critical_confirmation_result again\n'
    '            self.dismiss_confirm_dialog.emit()\n'
    '            return True\n'
)
assert old_yes in text, "yes_phrases block not found"
text = text.replace(old_yes, new_yes, 1)

# Fix 3: add dismiss_confirm_dialog signal
old_sigs = (
    '    nora_stopped = pyqtSignal()\n'
)
new_sigs = (
    '    nora_stopped = pyqtSignal()\n'
    '    dismiss_confirm_dialog = pyqtSignal()  # close popup without executing action\n'
)
assert old_sigs in text, "nora_stopped signal not found"
text = text.replace(old_sigs, new_sigs, 1)

open(path_vw, 'wb').write(text.encode('utf-8'))
print("voice_worker.py updated")

# Fix 4: app_controller.py - connect dismiss_confirm_dialog to close popup silently
path_ac = 'e:/projectnew/controller/app_controller.py'
text_ac = open(path_ac, 'rb').read().decode('utf-8')

old_connect = (
    '        w.nora_stopped.connect(self._on_nora_stopped)\n'
)
new_connect = (
    '        w.nora_stopped.connect(self._on_nora_stopped)\n'
    '        w.dismiss_confirm_dialog.connect(self.window.dismiss_confirm_dialog)\n'
)
assert old_connect in text_ac, "nora_stopped connect not found"
text_ac = text_ac.replace(old_connect, new_connect, 1)

open(path_ac, 'wb').write(text_ac.encode('utf-8'))
print("app_controller.py updated")

# Fix 5: main_window.py - add dismiss_confirm_dialog method that closes without callback
path_mw = 'e:/projectnew/ui/main_window.py'
text_mw = open(path_mw, 'rb').read().decode('utf-8')

old_voice_answer = (
    '    def voice_answer_confirm(self, text: str):\n'
    '        """Forward voice text to active confirmation dialog if present."""\n'
    '        dlg = getattr(self, "_active_confirm_dialog", None)\n'
    '        if dlg and dlg.isVisible():\n'
    '            dlg.voice_answer(text)\n'
)
new_voice_answer = (
    '    def voice_answer_confirm(self, text: str):\n'
    '        """Forward voice text to active confirmation dialog if present."""\n'
    '        # Voice already handled this - do not forward to avoid double-fire\n'
    '        pass\n'
    '\n'
    '    def dismiss_confirm_dialog(self):\n'
    '        """Close the confirmation dialog silently - voice already handled the answer."""\n'
    '        dlg = getattr(self, "_active_confirm_dialog", None)\n'
    '        if dlg and dlg.isVisible():\n'
    '            # Block signals so confirmed callback does NOT fire again\n'
    '            dlg.blockSignals(True)\n'
    '            dlg.reject()\n'
    '            dlg.blockSignals(False)\n'
    '        self._active_confirm_dialog = None\n'
)
assert old_voice_answer in text_mw, "voice_answer_confirm not found"
text_mw = text_mw.replace(old_voice_answer, new_voice_answer, 1)

open(path_mw, 'wb').write(text_mw.encode('utf-8'))
print("main_window.py updated")

# Verify syntax
for p in [path_vw, path_ac, path_mw]:
    try:
        py_compile.compile(p, doraise=True)
        print(f"Syntax OK: {p.split('/')[-1]}")
    except py_compile.PyCompileError as e:
        print(f"Syntax error in {p.split('/')[-1]}: {e}")
