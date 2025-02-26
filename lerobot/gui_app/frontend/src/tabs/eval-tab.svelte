<script>
import { onMount } from 'svelte';
import StopControlBtn from '../components/stop-control-btn.svelte';
import RobotConfigSelect from '../components/robot-config-select.svelte';
import PretrainedModelSelect from '../components/pretrained-model-select.svelte';

// Reactive variables for form fields
let robotConfigSelect = "";
let evalPolicyPath = "";
let evalRecordEpisodes = false;
let evalPushToHub = false;
let evalRoot = "data/eval_test";
let evalRepoID = "data/eval_test";
let evalTags = "";
let evalSingleTask = "";
let evalNumEpisodes = 50;
let evalWarmupTime = 5;
let evalEpisodeTime = 40;
let evalFPS = 30;
let evalImageWriterProcesses = 0;
let evalImageWriterThreads = 4;

// Options for the robot config select
let configOptions = [];
// Flag to show directory exists message
let evalDirExists = false;

// Start evaluation session
async function startEval() {
    try {
        await fetch("/robot/select_mode/eval", { method: "GET" });
    } catch (error) {
        console.error("Error starting eval session:", error);
    }
}

// Submit evaluation configuration form
async function submitEvalConfig(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    try {
        const response = await fetch(event.target.action, {
            method: event.target.method,
            body: formData
        });
        if (response.ok) {
            alert("Eval configuration updated successfully");
        } else {
            alert("Error updating eval configuration!!");
        }
    } catch (error) {
        console.error("Error updating eval configuration:", error);
        alert("Error updating eval configuration!!");
    }
}

// Check if the evaluation root directory exists
async function checkEvalRootDirExists(dirPath) {
    try {
        const response = await fetch('/api/check-directory-exists', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dir_path: dirPath })
        });
        if (!response.ok) {
            console.error("Failed to fetch directory status");
            return;
        }
        const data = await response.json();
        evalDirExists = data.exists;
    } catch (error) {
        console.error("Error checking directory exists:", error);
    }
}

// Handle input event for evalRoot field
function onEvalRootInput(e) {
    evalRoot = e.target.value;
    checkEvalRootDirExists(evalRoot);
}

// Load initial data when component mounts
onMount(async () => {

    // Fetch the initial evaluation configuration data
    try {
        const response = await fetch("/robot/get-control-config/eval");
        const data = await response.json();

        robotConfigSelect = data.robot_config;
        evalPolicyPath = data.pretrained_policy_path;
        evalRecordEpisodes = data.record_eval_episodes;
        evalPushToHub = data.push_to_hub;
        evalRoot = data.root;
        checkEvalRootDirExists(evalRoot);
        evalRepoID = data.repo_id;
        evalTags = data.tags;
        evalFPS = data.fps;
        evalEpisodeTime = data.episode_time_s;
        evalNumEpisodes = data.num_episodes;
        evalWarmupTime = data.warmup_time_s;
        evalImageWriterProcesses = data.num_image_writer_processes;
        evalImageWriterThreads = data.num_image_writer_threads_per_camera;
        evalSingleTask = data.single_task;
    } catch (error) {
        console.error("Error fetching eval configuration data:", error);
    }
});
</script>
  
  <div class="container">
  
    <!-- Eval control buttons -->
    <div class="card" style="background-color: var(--bs-gray-800)!important">
      <h6 class="card-header p-3">Mode Controls</h6>
      <div class="card-body pt-4 pb-4">  
        <button class="btn btn-primary me-2"
                on:click={startEval}
                data-bs-title="Start evaluating trained policy"
                data-bs-toggle="tooltip"
                data-bs-placement="bottom">
          <i class="bi bi-arrow-repeat"></i> 
          Start Evaluation
        </button>
        <StopControlBtn />
      </div>
    </div>
  
    <!-- Eval configuration accordion -->
    <div class="accordion mt-lg-4" id="evalAccordian">
      <div class="accordion-item">
        <h2 class="accordion-header">
          <button class="accordion-button"
                  type="button"
                  data-bs-toggle="collapse"
                  data-bs-target="#collapseEvalTab"
                  aria-expanded="true"
                  aria-controls="collapseEvalTab"
                  style="background-color: var(--bs-gray-800)!important">
            Configurations
          </button>
        </h2>
        <div id="collapseEvalTab" class="accordion-collapse collapse" data-bs-parent="#evalAccordian">
          <div class="accordion-body" style="background-color: var(--bs-gray-800)!important">
            <!-- Eval configuration form -->
            <form id="evalConfigForm"
                  action="/robot/eval/config-update"
                  method="post"
                  on:submit={submitEvalConfig}>
  
              <RobotConfigSelect />  
  
              <!-- <label for="evalPolicyPath" class="form-label">Pretrained Policy</label>
              <input type="text"
                     id="evalPolicyPath"
                     name="policy_path"
                     class="form-control"
                     bind:value={evalPolicyPath}
                     aria-describedby="recordHelpline">
              <div class="form-text">
                Path to the trained policy. e.g - outputs/train/act_so100_test/checkpoints/last/pretrained_model
              </div> -->
              <PretrainedModelSelect />
              
              <hr>
  
              <div class="container mb-2 d-flex flex-wrap">
                <div class="form-check form-switch me-2">
                  <input class="form-check-input"
                         name="record_episodes"
                         type="checkbox"
                         role="switch"
                         id="evalRecordEpisodes"
                         bind:checked={evalRecordEpisodes}>
                  <label class="form-check-label" for="evalRecordEpisodes">Record Eval Episodes</label>
                </div>
  
                <div class="form-check form-switch mb-3">
                  <input class="form-check-input"
                         name="push_to_hub"
                         type="checkbox"
                         role="switch"
                         id="evalPushToHub"
                         bind:checked={evalPushToHub}>
                  <label class="form-check-label" for="evalPushToHub">Push To Hub</label>
                </div>
              </div> 
  
              <label for="evalRoot" class="form-label">Root Dir</label>
              <input type="text"
                     id="evalRoot"
                     name="root_dir"
                     class="form-control"
                     bind:value={evalRoot}
                     on:input={onEvalRootInput}
                     aria-describedby="evalHelpline">
              <div class="form-text">
                Root directory where the dataset will be stored (e.g. 'dataset/path')
              </div>
              <div>
                {#if evalDirExists}
                  <small id="evalDirExistsMsg" style="color: red;">
                    Folder already exists!! Delete prev eval dataset folder.
                  </small>
                {/if}
              </div>
  
              <label for="evalRepoID" class="form-label mt-4">Repo ID</label>
              <input type="text"
                     id="evalRepoID"
                     name="repo_id"
                     class="form-control"
                     bind:value={evalRepoID}
                     aria-describedby="evalHelpline">
              <div class="form-text">
                Dataset identifier. By convention it should match 'hf_username/dataset_name' (e.g. <code>lerobot/test</code>)
              </div>
  
              <label for="evalTags" class="form-label mt-4">Tags</label>
              <input type="text"
                     id="evalTags"
                     name="tags"
                     class="form-control"
                     bind:value={evalTags}
                     aria-describedby="evalHelpline">
              <div class="form-text">Add tags to your dataset on the hub</div>
  
              <label for="evalSingleTask" class="form-label mt-4">Single Task Desc</label>
              <input type="text"
                     id="evalSingleTask"
                     name="single_task"
                     class="form-control"
                     bind:value={evalSingleTask}
                     aria-describedby="evalHelpline">
              <div class="form-text">
                A short but accurate description of the task performed during the recording
              </div>
  
              <label for="evalNumEpisodes" class="form-label mt-4">Num Episodes</label>
              <input type="number"
                     id="evalNumEpisodes"
                     name="num_episodes"
                     class="form-control"
                     bind:value={evalNumEpisodes}
                     aria-describedby="number of episodes">
              <div class="form-text">Number of episodes to evaluate</div>
              
              <label for="evalWarmupTime" class="form-label mt-4">Warmup Time</label>
              <input type="number"
                     id="evalWarmupTime"
                     name="warmup_time_s"
                     class="form-control"
                     bind:value={evalWarmupTime}
                     aria-describedby="warmup time">
              <div class="form-text">
                Warmup time before fetching cam feed and joint states
              </div>
              
              <hr>                            
  
              <div class="input-group mb-3">
                <span class="input-group-text">Max Episode Time</span>
                <input type="number"
                       class="form-control"
                       id="evalEpisodeTime"
                       name="episode_time_s"
                       bind:value={evalEpisodeTime}
                       aria-label="episode time">
                <span class="input-group-text">FPS</span>
                <input type="number"
                       class="form-control"
                       id="evalFPS"
                       name="fps"
                       bind:value={evalFPS}
                       aria-label="frames per second">
                <div class="form-text">
                  Max time per episode in seconds within which the episode is to be recorded.
                  Safety feature implemented to prevent infinite loop execution. FPS to evaluate.
                </div>
              </div>
  
              <div class="input-group mb-3">
                <span class="input-group-text">Image Writer Processes</span>
                <input type="number"
                       class="form-control"
                       id="evalImageWriterProcesses"
                       name="num_image_writer_processes"
                       bind:value={evalImageWriterProcesses}
                       aria-label="number of processes for image writer">
                <span class="input-group-text">Writer Threads</span>
                <input type="number"
                       class="form-control"
                       id="evalImageWriterThreads"
                       name="num_image_writer_threads_per_camera"
                       bind:value={evalImageWriterThreads}
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
  