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
  
<div class="card mb-3" style="background-color: var(--bs-gray-800)!important">
    <div class="card-body">
        <label for="robotConfigSelect" class="form-label">Robot Type</label>
        <select id="robotConfigSelect" class="form-select" name="robot_config" disabled>
            {#each configs as config}
            <option value={config}>{config}</option>
            {/each}
        </select>
    </div>    
</div>
  