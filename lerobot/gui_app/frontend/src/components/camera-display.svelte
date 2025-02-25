<script>
import { onMount } from 'svelte';

let cameras = [];
let loading = true;
let error = '';

onMount(async () => {
    try {
        const response = await fetch("/robot/cameras");
        cameras = await response.json();
    } catch (err) {
        console.error("Error fetching camera data:", err);
        error = "Error fetching camera data";
    } finally {
        loading = false;
    }
});
</script>

<div id="cameraContainer" class="d-flex justify-content-end p-0 m-0">
    {#if loading}
        <p>Loading cameras...</p>
    {:else if error}
        <p class="text-danger">{error}</p>
    {:else if cameras.length === 0}
        <h5 class="mt-4 text-warning-emphasis">
            No cameras found. Check for connection issues!!
        </h5>
    {:else}
        {#each cameras as camera (camera.id)}
        <div class="card m-4 overflow-hidden" style="width: 320px; height: 280px;">
            <div class="card-body p-2" style="background-color: var(--bs-gray-800)!important;">
            <p class="card-text fst-italic">{camera.name}</p>
            </div>
            <img class="card-img-bottom" alt="{camera.name}" src="{camera.video_url}" />
        </div>
        {/each}
    {/if}
</div>
  