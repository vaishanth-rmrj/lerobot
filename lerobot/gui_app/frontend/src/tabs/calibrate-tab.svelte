<script>
import { onMount } from 'svelte';

// Reactive arrays to store arms and cameras data
let arms = [];
let cameras = [];

// Fetch arms and cameras when the component mounts
onMount(async () => {
    // Fetch available arm names
    try {
        const response = await fetch('/api/calibrate/get-arms-name');
        const data = await response.json();
        arms = data;
    } catch (error) {
        console.error('Error fetching arm names:', error);
    }
    
    // Fetch connected camera information
    try {
        const response = await fetch('/api/calibrate/get-connected-cams-port');
        const data = await response.json();
        cameras = data;
    } catch (error) {
        console.error('Error fetching camera data:', error);
    }
});
</script>
  
  <div class="container">
    <!-- Card for available arms -->
    <div class="card" style="background-color: var(--bs-gray-800)!important">
      <h6 class="card-header p-3">Available Arms</h6>
      <ul class="list-group list-group-flush" id="calibrateAvailableArms">
        {#if arms.length === 0}
          <p class="p-4 mt-2 mb-2 text-warning">
            No arms found !! Check for connection issues or incorrect config file.
          </p>
        {:else}
          {#each arms as arm}
            <li class="list-group-item p-3" style="background-color: var(--bs-gray-800)!important">
              <div class="d-flex justify-content-between align-items-center">
                <strong>{arm}</strong>
              </div>
            </li>
          {/each}
        {/if}
      </ul>
      <div class="card-body">
        <small class="form-text mb-4">
          Run calibration using the following CLI Command:
        </small>
        <small class="form-text">          
          {@html `<pre><code>python lerobot/scripts/control_robot.py \\
            --robot.type=so100 \\
            --robot.cameras='{}' \\
            --control.type=calibrate \\
            --control.arms='["main_follower"]'
          </code></pre>`}        
        </small>
      </div>
    </div>
  
    <!-- Card for available cameras -->
    <div class="card mt-4" style="background-color: var(--bs-gray-800)!important">
      <h6 class="card-header p-3">Available Cameras</h6>
      <ul class="list-group list-group-flush" id="availableCameras">
        {#if cameras.length === 0}
          <p class="p-4 mt-2 mb-2 text-warning">
            No cameras found !! Check for connection issues or incorrect config file.
          </p>
        {:else}
          {#each cameras as camera, index}
            <li class="list-group-item p-3" style="background-color: var(--bs-gray-800)!important">
              <div class="d-flex justify-content-between">
                <strong>Camera {index}</strong>
                <strong>Index: {camera.index}</strong>
                <strong>Port: {camera.port}</strong>
              </div>
            </li>
          {/each}
        {/if}
      </ul>
    </div>
  </div>
  