<script>
import { onMount } from 'svelte';

let { policyPath } = $props();
let policyRunPath = $state("");

let availabelPretrainedmodels = $state([]);
let selectedPolicyFullPath = $state("");
let selectedPolicyPath= $state('');
let selectedCheckpoint = $state('');
let availableCheckpoints = $state([]);

function extractPolicyPathAndCheckpoint(path) {
    const parts = path.split("/");

    // extract checkpoint number and policy run path
    const checkpointIndex = parts.indexOf("checkpoints");
    const checkpointNum = parts[checkpointIndex + 1];
    const policyRunPath = parts.slice(checkpointIndex - 2, checkpointIndex).join("/");
    return { policyRunPath, checkpointNum };
}

// Fetch data from the FastAPI endpoint when the component mounts
onMount(async () => {

    setTimeout(async () => {
        console.log("policyPath:", policyPath);

        let res = extractPolicyPathAndCheckpoint(policyPath);
        policyRunPath = res.policyRunPath;
        selectedCheckpoint = res.checkpointNum;

        try {
            const res = await fetch('/api/get-pretrained-models-info');
            if (res.ok) {
                availabelPretrainedmodels = await res.json();
                availabelPretrainedmodels = availabelPretrainedmodels?.sort();
                availabelPretrainedmodels.forEach(model => {
                    if (model.date+"/"+model.run_name === policyRunPath) {
                        availableCheckpoints = model.checkpoints?.sort();
                    }
                });
            } else {
                console.error('Error fetching availabel pretrained models:', res.statusText);
            }
        } catch (error) {
            console.error('Fetch error:', error);
        }    
    
    }, 1000);
    
});

// Update the checkpoints when a new model is selected
function handleModelChange(event) {
    const selectedIndex = event.target.selectedIndex;
    availableCheckpoints = availabelPretrainedmodels[selectedIndex].checkpoints.sort();

    selectedPolicyPath = event.target.value;
    selectedCheckpoint = availableCheckpoints[0];    
    selectedPolicyFullPath = `${selectedPolicyPath}/checkpoints/${selectedCheckpoint}/pretrained_model`;
}

// Update the selected checkpoint value
function handleCheckpointChange(event) {
    selectedCheckpoint = event.target.value;
    selectedPolicyFullPath = `${selectedPolicyPath}/checkpoints/${selectedCheckpoint}/pretrained_model`;
}
</script>

<div class="d-flex">
<!-- Model Path Selection -->
<div style="max-width: 80%;">
    <label for="model-select" class="form-label">Pretrained Model</label>
    <!-- Hidden select bound to the computed policyPath -->
    <select hidden name="policy_path" bind:value={selectedPolicyFullPath}>
        <option value={selectedPolicyFullPath}>{selectedPolicyFullPath}</option>
    </select>

    <select id="model-select" class="form-select"  onchange={handleModelChange}>
        {#each availabelPretrainedmodels as model}
        <option value={model.dir_path} selected={model.date+"/"+model.run_name === policyRunPath}>
            {model.date} | {model.run_name} 
        </option>
        {/each}
    </select>
    
</div>


<!-- Checkpoint Selection -->
<div>
    <label for="checkpoint-select" class="form-label">Checkpoint</label>
    <select id="checkpoint-select" class="form-select" onchange={handleCheckpointChange}>
        {#each availableCheckpoints as checkpoint}
        <option value={checkpoint} selected={checkpoint === selectedCheckpoint}>
            {checkpoint}
        </option>
        {/each}
    </select>
</div>

</div>
  