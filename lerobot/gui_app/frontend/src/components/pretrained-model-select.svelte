<script>
import { onMount } from 'svelte';

let models = [];
let selectedModel = null;
let checkpoints = [];
let selectedCheckpoint = '';

$: policyPath = selectedModel ? `${selectedModel.dir_path}/checkpoints/${selectedCheckpoint}/pretrained_model`: '';

// Fetch data from the FastAPI endpoint when the component mounts
onMount(async () => {
    try {
    const res = await fetch('/api/get-pretrained-models-info');
    if (res.ok) {
        models = await res.json();
        if (models.length > 0) {
            selectedModel = models[0];
            checkpoints = selectedModel.checkpoints;
            selectedCheckpoint = checkpoints[0];
        }
    } else {
        console.error('Error fetching models:', res.statusText);
    }
    } catch (error) {
    console.error('Fetch error:', error);
    }
});

// Update the checkpoints when a new model is selected
function handleModelChange(event) {
    const selectedIndex = event.target.selectedIndex;
    selectedModel = models[selectedIndex];
    checkpoints = selectedModel.checkpoints;
    // Reset the checkpoint selection
    selectedCheckpoint = checkpoints[0];
}

// Update the selected checkpoint value
function handleCheckpointChange(event) {
    selectedCheckpoint = event.target.value;
}
</script>

<div class="d-flex">
<!-- Model Path Selection -->
<div style="max-width: 80%;">
    <label for="model-select" class="form-label">Pretrained Model</label>
    <!-- Hidden select bound to the computed policyPath -->
    <select hidden name="policy_path" bind:value={policyPath}>
        <option value={policyPath}>{policyPath}</option>
    </select>

    <select id="model-select" class="form-select"  onchange={handleModelChange}>
        {#each models as model}
        <option value={model.dir_path}>
            {model.date} | {model.run_name} 
        </option>
        {/each}
    </select>
    
</div>


<!-- Checkpoint Selection -->
<div>
    <label for="checkpoint-select" class="form-label">Checkpoint</label>
    <select id="checkpoint-select" class="form-select" onchange={handleCheckpointChange}>
        {#each checkpoints as checkpoint}
        <option value={checkpoint}>
            {checkpoint}
        </option>
        {/each}
    </select>
</div>

</div>
  