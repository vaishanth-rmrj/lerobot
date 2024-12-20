// js for record gui controls

document.getElementById("startRecordSessionBtn")
.addEventListener("click", async () => {
    try {
        await fetch("/select_mode/record", { method: "GET" });
    } catch (error) {
        console.error("Error starting record session:", error);
    }
});

document.getElementById("stopRecordSessionBtn")
.addEventListener("click", async () => {
    try {
        await fetch("/stop", { method: "GET" });
    } catch (error) {
        console.error("Error stopping record session:", error);
    }
});

document.getElementById("startRecordBtn")
.addEventListener("click", async () => {
    try {
        await fetch("/record/start_recording", { method: "GET" });
    } catch (error) {
        console.error("Error recording:", error);
    }
});

document.getElementById("finishRecordBtn")
.addEventListener("click", async () => {
    try {
        await fetch("/record/finish_recording", { method: "GET" });
    } catch (error) {
        console.error("Error finishing recording:", error);
    }
});

document.getElementById("cancelRecordBtn")
.addEventListener("click", async () => {
    try {
        await fetch("/record/cancel_recording", { method: "GET" });
    } catch (error) {
        console.error("Error cancelling recording:", error);
    }
});



// config form funcs
document.getElementById('recordConfigForm')
.addEventListener('submit', async (event) => {
    event.preventDefault();

    const formData = new FormData(recordConfigForm);
    const response = await fetch(recordConfigForm.action, {
        method: recordConfigForm.method,
        body: formData
    });

    if (response.ok) {
        alert('Record configuration updated successfully');
    } else {
        alert('Error updating record configuration!!');
    }
});

document.addEventListener("DOMContentLoaded", async () => {
    const form = document.getElementById("recordConfigForm");

    try {
        // fetch data from the backend
        const response = await fetch("/record/get-config");
        const data = await response.json();

        // map backend data to form fields
        form.robotConfigSelect.value = data.robot_config;
        form.recordRoot.value = data.root;
        form.recordRepoID.value = data.repo_id;
        form.recordTags.value = data.tags;
        form.recordFPS.value = data.fps;

        form.resumeRecordToggle.checked = data.resume;
        form.recordLocalFilesToggle.checked = data.local_files_only;
        form.recordRunComputeStats.checked = data.run_compute_stats;
        form.recordPushToHub.checked = data.push_to_hub;

        form.recordEpisodeTime.value = data.episode_time_s;
        form.recordNumEpisodes.value = data.num_episodes;

        form.recordImageWriterProcesses.value = data.num_image_writer_processes;
        form.recordImageWriterThreads.value = data.num_image_writer_threads_per_camera;
        form.recordSingleTask.value = data.single_task;

    } catch (error) {
        console.error("Error fetching record configuration data:", error);
    }
});