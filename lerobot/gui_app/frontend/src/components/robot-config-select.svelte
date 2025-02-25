<script>
import { onMount } from 'svelte';

let configs = [];

onMount(async () => {
    try {
        const response = await fetch("/robot/configs-path");
        const data = await response.json();
        configs = data;
    } catch (error) {
        console.error("Error fetching robot configs:", error);
    }
});
</script>
  
<div class="mb-3">
    <label for="robotConfigSelect" class="form-label">Robot Config</label>
    <select id="robotConfigSelect" class="form-select" name="robot_config">
        {#each configs as config}
        <option value={config}>{config}</option>
        {/each}
    </select>
    <small class="form-text">Path to robot config file</small>
</div>
  