<script>
import { onMount } from 'svelte';
import StopControlBtn from '../components/stop-control-btn.svelte';
import RobotConfigSelect from '../components/robot-config-select.svelte';
import DatasetRootdirInput from '../components/dataset-rootdir-input.svelte';

// Form fields for record configuration.
let robotConfigSelect = "";
let recordRoot = "data/";
let recordRepoID = "default/dataset";
let recordTags = "";
let recordFPS = 30;
let resumeRecordToggle = false;
let recordLocalFilesToggle = false;
let recordRunComputeStats = true;
let recordPushToHub = false;
let recordEpisodeTime = 40;
let recordNumEpisodes = 50;
let recordImageWriterProcesses = 0;
let recordImageWriterThreads = 4;
let recordSingleTask = "";

// Flag to indicate if the record root directory exists.
let recordDirExists = false;

// Options for the robot config select field.
let configOptions = [];

// Fetch configuration options and record config on component mount.
onMount(async () => {

    // Fetch the initial record configuration.
    try {
        const response = await fetch("/robot/get-control-config/record");
        const data = await response.json();

        robotConfigSelect = data.robot_config;
        recordRoot = data.root;
        recordRepoID = data.repo_id;
        recordTags = data.tags;
        recordFPS = data.fps;
        resumeRecordToggle = data.resume;
        recordLocalFilesToggle = data.local_files_only;
        recordRunComputeStats = data.run_compute_stats;
        recordPushToHub = data.push_to_hub;
        recordEpisodeTime = data.episode_time_s;
        recordNumEpisodes = data.num_episodes;
        recordImageWriterProcesses = data.num_image_writer_processes;
        recordImageWriterThreads = data.num_image_writer_threads_per_camera;
        recordSingleTask = data.single_task;
    } catch (error) {
        console.error("Error fetching record configuration data:", error);
    }
});

// Control button functions.
async function startRecordSession() {
    try {
        await fetch("/robot/select_mode/record", { method: "GET" });
    } catch (error) {
        console.error("Error starting record session:", error);
    }
}

// Stub for activateEvent (sends a POST with an event name).
async function activateEvent(eventName) {
    try {
        const response = await fetch(`/robot/activate-event`, {
            method: "POST",
            headers: {
            "Content-Type": "application/json"
            },
            body: JSON.stringify({ event: eventName })
        });
        const result = await response.json();
        return result.success;
    } catch (error) {
        console.error("Error activating event:", error);
    return false;
    }
}

async function startRecord() {
    const success = await activateEvent("start_recording");
    console.log(success ? "Event activated successfully" : "Failed to activate event");
}

async function finishRecord() {
    const success = await activateEvent("finish_recording");
    console.log(success ? "Event activated successfully" : "Failed to activate event");
}

async function cancelRecord() {
    const success = await activateEvent("discard_recording");
    console.log(success ? "Event activated successfully" : "Failed to activate event");
}

// Handle form submission for record configuration.
async function submitRecordConfig(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    try {
        const response = await fetch(event.target.action, {
            method: event.target.method,
            body: formData
        });
        if (response.ok) {
            alert("Record configuration updated successfully");
        } else {
            alert("Error updating record configuration!!");
        }
    } catch (error) {
        console.error("Error updating record configuration:", error);
        alert("Error updating record configuration!!");
    }
}
</script>
  
  <div class="container">
    <!-- Record control buttons -->
    <div class="card" style="background-color: var(--bs-gray-800)!important">
      <h6 class="card-header p-3">Mode Controls</h6>
      <div class="card-body pt-4 pb-4">
        <button class="btn btn-primary me-2"
                on:click={startRecordSession}
                data-bs-title="Only start control loop"
                data-bs-toggle="tooltip"
                data-bs-placement="bottom">
          <i class="bi bi-arrow-repeat"></i> 
          Start Session
        </button>
        <StopControlBtn />
  
        <hr>
        <small>Dataset record controls. Make sure session is running!</small>
  
        <div class="mt-3">
          <button class="btn btn-success me-2"
                  on:click={startRecord}
                  data-bs-title="Trigger dataset recording (Shortcut: 'r' key)"
                  data-bs-toggle="tooltip"
                  data-bs-placement="bottom">
            <i class="bi bi-record-fill"></i> 
            Record
          </button>
          <button class="btn btn-primary me-2"
                  on:click={finishRecord}
                  data-bs-title="Finish and save recorded data. (Shortcut: Right Arrow)"
                  data-bs-toggle="tooltip"
                  data-bs-placement="bottom">
            <i class="bi bi-save-fill"></i> 
            Finish
          </button>
          <button class="btn btn-danger me-2"
                  on:click={cancelRecord}
                  data-bs-title="Cancel and del recorded data. (Shortcut: Left Arrow)"
                  data-bs-toggle="tooltip"
                  data-bs-placement="bottom">
            <i class="bi bi-trash3-fill"></i> 
            Cancel
          </button>
        </div>
      </div>
    </div>
  
    <!-- Record configuration accordion -->
    <div class="accordion mt-lg-4" id="recordAccordian">
      <div class="accordion-item">
        <h2 class="accordion-header">
          <button class="accordion-button"
                  type="button"
                  data-bs-toggle="collapse"
                  data-bs-target="#collapseRecordTab"
                  aria-expanded="true"
                  aria-controls="collapseRecordTab"
                  style="background-color: var(--bs-gray-800)!important">
            Configurations
          </button>
        </h2>
        <div id="collapseRecordTab" class="accordion-collapse collapse" data-bs-parent="#recordAccordian">
          <div class="accordion-body" style="background-color: var(--bs-gray-800)!important">
            <!-- Configuration form -->
            <form id="recordConfigForm"
                  action="/robot/record/config-update"
                  method="post"
                  on:submit={submitRecordConfig}>
  
              <RobotConfigSelect />  
              <hr>
              
              <DatasetRootdirInput rootDirInputName="root_dir" rootDir={recordRoot} />
  
              <label for="recordRepoID" class="form-label mt-4">Repo ID</label>
              <input type="text"
                     id="recordRepoID"
                     name="repo_id"
                     class="form-control"
                     aria-describedby="recordHelpline"
                     bind:value={recordRepoID}>
              <div class="form-text">
                Dataset identifier. By convention it should match 'hf_username/dataset_name' (e.g. <code>lerobot/test</code>)
              </div>
  
              <label for="recordTags" class="form-label mt-4">Tags</label>
              <input type="text"
                     id="recordTags"
                     name="tags"
                     class="form-control"
                     aria-describedby="recordHelpline"
                     bind:value={recordTags}>
              <div class="form-text">Add tags to your dataset on the hub</div>
                
              <label for="recordSingleTask" class="form-label mt-4">Single Task Desc</label>
              <input type="text"
                     id="recordSingleTask"
                     name="single_task"
                     class="form-control"
                     aria-describedby="recordHelpline"
                     bind:value={recordSingleTask}>
              <div class="form-text">
                A short but accurate description of the task performed during the recording
              </div>
  
              <label for="recordNumEpisodes" class="form-label mt-4">Num Episodes</label>
              <input type="number"
                     id="recordNumEpisodes"
                     name="num_episodes"
                     class="form-control"
                     aria-describedby="number of episodes"
                     bind:value={recordNumEpisodes}>
              <div class="form-text">Number of episodes to record</div>
  
              <hr>
              <div class="container mb-2 d-flex flex-wrap">
                <div class="form-check form-switch" style="margin-right: 10px;">
                  <input class="form-check-input"
                         name="resume"
                         type="checkbox"
                         role="switch"
                         id="resumeRecordToggle"
                         bind:checked={resumeRecordToggle}>
                  <label class="form-check-label" for="resumeRecordToggle">Resume</label>
                </div>
  
                <div class="form-check form-switch" style="margin-right: 10px;">
                  <input class="form-check-input"
                         name="local_files_only"
                         type="checkbox"
                         role="switch"
                         id="recordLocalFilesToggle"
                         bind:checked={recordLocalFilesToggle}>
                  <label class="form-check-label" for="recordLocalFilesToggle">Local Files Only</label>
                </div>
  
                <div class="form-check form-switch mb-3">
                  <input class="form-check-input"
                         name="run_compute_stats"
                         type="checkbox"
                         role="switch"
                         id="recordRunComputeStats"
                         bind:checked={recordRunComputeStats}>
                  <label class="form-check-label" for="recordRunComputeStats">Run Compute Stats</label>
                </div>
  
                <div class="form-check form-switch mb-3">
                  <input class="form-check-input"
                         name="push_to_hub"
                         type="checkbox"
                         role="switch"
                         id="recordPushToHub"
                         bind:checked={recordPushToHub}>
                  <label class="form-check-label" for="recordPushToHub">Push To Hub</label>
                </div>
              </div>
  
              <div class="input-group mb-3">
                <span class="input-group-text">Max Episode Time</span>
                <input type="number"
                       class="form-control"
                       id="recordEpisodeTime"
                       name="episode_time_s"
                       bind:value={recordEpisodeTime}
                       aria-label="episode time">
                <span class="input-group-text">FPS</span>
                <input type="number"
                       class="form-control"
                       id="recordFPS"
                       name="fps"
                       bind:value={recordFPS}
                       aria-label="frames per second">
                <div class="form-text">
                  Max time per episode in seconds within which the episode is to be recorded.
                  Safety feature implemented to prevent infinite loop execution. FPS to record.
                </div>
              </div>
  
              <div class="input-group mb-3">
                <span class="input-group-text">Image Writer Processes</span>
                <input type="number"
                       class="form-control"
                       id="recordImageWriterProcesses"
                       name="num_image_writer_processes"
                       bind:value={recordImageWriterProcesses}
                       aria-label="number of processes for image writer">
                <span class="input-group-text">Writer Threads</span>
                <input type="number"
                       class="form-control"
                       id="recordImageWriterThreads"
                       name="num_image_writer_threads_per_camera"
                       bind:value={recordImageWriterThreads}
                       aria-label="number of threads for image writer">
                <div class="form-text">
                  Number of subprocesses for saving frames as PNGs. Set to 0 to use threads only; ≥1 to use subprocesses with threads.
                  Recommended: 4 threads per camera with 0 processes. Adjust thread count if FPS is unstable; if still unstable, try using subprocesses.
                </div>
              </div>
  
              <div class="d-grid gap-2 col-6 mx-auto mt-4">
                <button type="submit" class="btn btn-warning">Apply</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  </div>
  