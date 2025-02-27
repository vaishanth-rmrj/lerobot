<script>
import { onMount } from "svelte";

let { rootDirInputName,  rootDir = "data/test"} = $props();
let isDirExists = $state(false);

// Check if the record root directory exists.
async function checkRootDirExists(dirPath) {
    console.log("Checking if directory exists:", dirPath);
    try {
        const response = await fetch('/api/check-directory-exists', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ dir_path: dirPath })
        });
        if (!response.ok) {
            console.error("Failed to fetch directory status");
            return;
        }
        const data = await response.json();
        isDirExists = data.exists;
    } catch (error) {
        console.error("Error checking directory exists:", error);
    }
}

// handle input changes for the rootDir field.
async function onRootInput(e) {
    rootDir = e.target.value;
    await checkRootDirExists(rootDir);
}

onMount(async () => {
    setTimeout(async () => {
        await checkRootDirExists(rootDir);
    }, 1000);
});

</script>

<label for="rootDir" class="form-label">Root Dir</label>
<input type="text"
        id="rootDir"
        name="{rootDirInputName}"
        class="form-control"
        aria-describedby="recordHelpline"
        bind:value={rootDir}
        oninput={onRootInput}>
<div class="form-text">
    Root directory where the dataset will be stored (e.g. 'dataset/path')
</div>
<div>
{#if isDirExists}
    <small class="text-danger">
        Folder already exists!! Either turn on resume or del prev dataset folder.
    </small>
{/if}
</div>