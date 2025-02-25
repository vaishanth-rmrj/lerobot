<script>
import Navbar from "./components/navbar.svelte";
import CameraDisplay from "./components/camera-display.svelte";
import StateActionDisplay from "./components/state-action-display.svelte";
import ActionBar from "./components/action-bar.svelte";
import LogsDisplay from "./components/logs-display.svelte";
import ErrorToast from "./components/error-toast.svelte";
import AlertToast from "./components/alert-toast.svelte";

// tabs
import TeleopTab from "./tabs/teleop-tab.svelte";
import RecordTab from "./tabs/record-tab.svelte";
import EvalTab from "./tabs/eval-tab.svelte";
import CalibrateTab from "./tabs/calibrate-tab.svelte";

// enable tooltips
// const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
// tooltipTriggerList.forEach(t => {
//     new bootstrap.Tooltip(t);
// })
</script>

<Navbar />

<div class="container-fluid d-flex justify-content-center align-items-center mt-4">
  <CameraDisplay />
  <StateActionDisplay />
</div>

<div class="container">
  <div class="row">

    <div class="col-6">
      <div class="container p-4">

        <ActionBar />

        <ul class="nav nav-tabs" id="myTab" role="tablist">
            <li class="nav-item " role="presentation">
              <button class="nav-link active" id="teleop-tab" data-bs-toggle="tab" data-bs-target="#teleop-tab-pane" type="button" role="tab" aria-controls="teleop-tab-pane" aria-selected="true" style="font-weight: bold;">Teleop</button>
            </li>
            <li class="nav-item" role="presentation">
              <button class="nav-link" id="record-tab" data-bs-toggle="tab" data-bs-target="#record-tab-pane" type="button" role="tab" aria-controls="record-tab-pane" aria-selected="false" style="font-weight: bold;">Record</button>
            </li>
            <li class="nav-item" role="presentation">
              <button class="nav-link" id="eval-tab" data-bs-toggle="tab" data-bs-target="#eval-tab-pane" type="button" role="tab" aria-controls="eval-tab-pane" aria-selected="false" style="font-weight: bold;">Evaluate</button>
            </li>
            <li class="nav-item" role="presentation">
              <button class="nav-link" id="calibrate-tab" data-bs-toggle="tab" data-bs-target="#calibrate-tab-pane" type="button" role="tab" aria-controls="calibrate-tab-pane" aria-selected="false" style="font-weight: bold;">Calibrate</button>
            </li>
        </ul>

        <div class="tab-content border border-top-0 rounded pt-3 pb-3" id="myTabContent">

            <div class="tab-pane fade show active" id="teleop-tab-pane" role="tabpanel" aria-labelledby="teleop-tab" >
              <TeleopTab />
            </div>
            
            <div class="tab-pane fade" id="record-tab-pane" role="tabpanel" aria-labelledby="record-tab" >
              <RecordTab />
            </div>

            <div class="tab-pane fade" id="eval-tab-pane" role="tabpanel" aria-labelledby="eval-tab" >
              <EvalTab />
            </div>

            <div class="tab-pane fade" id="calibrate-tab-pane" role="tabpanel" aria-labelledby="calibrate-tab" >
              <CalibrateTab />
            </div>               

        </div>
      </div>
    </div>

    <div class="col-6" style="margin-top: 22px;">      
      <LogsDisplay />
    </div>
  </div>
</div>

<ErrorToast />
<AlertToast />



