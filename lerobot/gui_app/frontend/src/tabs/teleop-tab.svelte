<script>
import { onMount } from 'svelte';
import { errorMessages } from '../stores/error-msg-store';
import { alertMessages } from '../stores/alert-msg-store';
import StopControlBtn from '../components/stop-control-btn.svelte';
import RobotConfigSelect from '../components/robot-config-select.svelte';

let robotConfig = "";
let fps = $state(30);

// start teleop control loop
async function startTeleop() {
    try {
        await fetch("/robot/select_mode/teleop", { method: "GET" });
        alertMessages.update((alerts) => [...alerts, "Started Teleop Control"]);
    } catch (error) {
        errorMessages.update((errors) => [...errors, `Error starting teleoperation!! ${error.message || error}`]);
    }
}

async function updateTeleopConfig(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    try {
        const response = await fetch(event.target.action, {
            method: event.target.method,
            body: formData,
        });
        if (response.ok) {
            alertMessages.update((alerts) => [...alerts, "Teleop configuration updated successfully"]);
        } else {
            errorMessages.update((errors) => [...errors, "Error updating teleop configuration!!"]);
        }
    } catch (error) {
        errorMessages.update((errors) => [...errors, `Error updating teleop configuration: ${error.message || error}`]);
    }
}

onMount(async () => {

    try {
        const response = await fetch("/robot/get-control-config/teleop");
        const data = await response.json();
        robotConfig = data.robot_config;
        fps = data.fps;
    } catch (error) {
        errorMessages.update((errors) => [...errors, `Error fetching configuration data: ${error.message || error}`]);
    }

});

</script>
  
<div class="container">

<!-- Teleop control buttons -->
<div class="card" style="background-color: var(--bs-gray-800)!important">
    <h6 class="card-header p-3">Mode Controls</h6>
    <div class="card-body pt-4 pb-4">
        <button
            class="btn btn-primary me-2"
            onclick={startTeleop}
            data-bs-title="Start teleop control loop"
            data-bs-toggle="tooltip"
            data-bs-placement="bottom">
            <i class="bi bi-arrow-repeat"></i>
            Start Teleop
        </button>
        <StopControlBtn />    
    </div>
</div>

<!-- Teleop configuration -->
<div class="accordion mt-4" id="teleopAccordians">
    <div class="accordion-item">
    <h2 class="accordion-header">
        <button
        class="accordion-button"
        type="button"
        data-bs-toggle="collapse"
        data-bs-target="#collapseOne"
        aria-expanded="true"
        aria-controls="collapseOne"
        style="background-color: var(--bs-gray-800)!important">
        Configurations
        </button>
    </h2>
    <div id="collapseOne" class="accordion-collapse collapse" data-bs-parent="#teleopAccordians">
        <div class="accordion-body" style="background-color: var(--bs-gray-800)!important">
            <!-- Configuration Form -->
            <form
                id="teleopConfigForm"
                action="/robot/telop/config-update"
                method="post"
                onsubmit={updateTeleopConfig}>

                <RobotConfigSelect />
                <hr>

                <label for="teleopFPS" class="form-label mt-2">FPS</label>
                <input
                    type="number"
                    id="teleopFPS"
                    name="fps"
                    class="form-control"
                    bind:value={fps}
                    aria-describedby="teleopHelpInline">
                <small class="form-text">Frames per second to perform teleop</small>

                <div class="d-grid gap-2 col-6 mx-auto mt-4">
                    <button type="submit" class="btn btn-warning">Apply</button>
                </div>
            </form>
        </div>
    </div>
    </div>
</div>
</div>
  