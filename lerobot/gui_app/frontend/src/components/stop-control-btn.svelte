<script>
import { errorMessages } from '../stores/error-msg-store';
import { alertMessages } from '../stores/alert-msg-store';
// stop control loop
async function stopControlLoop() {
    try {
        await fetch("/robot/stop", { method: "GET" });
        alertMessages.update((alerts) => [...alerts, "Stopped control loop"]);

    } catch (error) {
        errorMessages.update((errors) => [...errors, `Error stopping teleoperation!! ${error.message || error}`]);

    }
}
</script>

<button
    class="btn btn-danger me-2"
    on:click={stopControlLoop}
    data-bs-title="Stop control loop"
    data-bs-toggle="tooltip"
    data-bs-placement="bottom">
    <i class="bi bi-ban"></i>
    Stop
</button>