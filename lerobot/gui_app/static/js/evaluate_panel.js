// js for eval gui controls

document.getElementById("startEvalBtn")
.addEventListener("click", async () => {
    try {
        await fetch("/select_mode/eval", { method: "GET" });
    } catch (error) {
        console.error("Error starting eval session:", error);
    }
});

document.getElementById("stopEvalBtn")
.addEventListener("click", async () => {
    try {
        await fetch("/stop", { method: "GET" });
    } catch (error) {
        console.error("Error stopping eval session:", error);
    }
});

document.getElementById('evalConfigForm')
.addEventListener('submit', async (event) => {
    event.preventDefault(); 

    const formData = new FormData(evalConfigForm);
    const response = await fetch(evalConfigForm.action, {
        method: evalConfigForm.method,
        body: formData
    });

    if (response.ok) {
        alert('Eval configuration updated successfully');
    } else {
        alert('Error updating eval configuration!!');
    }
});

document.addEventListener("DOMContentLoaded", async () => {
    const form = document.getElementById("evalConfigForm");

    try {
        // fetch data from the backend
        const response = await fetch("/robot/eval/get-config");
        const data = await response.json();

        // map backend data to form fields
        form.robotConfigSelect.value = data.robot_config;
        form.evalPolicyPath.value = data.pretrained_policy_path;
        form.evalRecordEpisodes.checked = data.record_eval_episodes;
        form.evalPushToHub.checked = data.push_to_hub;

        form.evalRoot.value = data.root;
        form.evalRepoID.value = data.repo_id;
        form.evalTags.value = data.tags;
        form.evalFPS.value = data.fps;       

        form.evalEpisodeTime.value = data.episode_time_s;
        form.evalNumEpisodes.value = data.num_episodes;
        form.evalWarmupTime.value = data.warmup_time_s;

        form.evalImageWriterProcesses.value = data.num_image_writer_processes;
        form.evalImageWriterThreads.value = data.num_image_writer_threads_per_camera;
        form.evalSingleTask.value = data.single_task;

    } catch (error) {
        console.error("Error fetching eval configuration data:", error);
    }
});