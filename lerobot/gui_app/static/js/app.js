//   async function updateStatus() {
//     try {
//       const response = await fetch("/teleoperation/status");
//       const data = await response.json();
//       const statusDiv = document.getElementById("status");
//       statusDiv.textContent = `Status: ${
//         data.running ? "Running" : "Stopped"
//       }`;
//       statusDiv.className = data.running ? "running" : "stopped";
//     } catch (error) {
//       console.error("Error fetching status:", error);
//     }
//   }

document.addEventListener("DOMContentLoaded", async () => {

    const teleopRobotConfigForm = document.getElementById("teleopConfigForm");
    const teleopRobotConfigSelect = teleopRobotConfigForm.querySelector("#robotConfigSelect");

    const recordRobotConfigForm = document.getElementById("recordConfigForm");
    const recordRobotConfigSelect = recordRobotConfigForm.querySelector("#robotConfigSelect");

    try {
        // Fetch the list of cameras from the backend
        const response = await fetch("/robot/configs-path");
        const configsPath = await response.json();

        // <option>lerobot/configs/robot/so100.yaml</option>

        // Clear existing options
        recordRobotConfigSelect.innerHTML = "";
        teleopRobotConfigSelect.innerHTML = "";

        // Populate the <select> element with options
        configsPath.forEach(path => {
            const recordOption = document.createElement("option");
            recordOption.value = path;
            recordOption.textContent = path;
            recordRobotConfigSelect.appendChild(recordOption);

            const teleopOption = document.createElement("option");
            teleopOption.value = path;
            teleopOption.textContent = path;
            teleopRobotConfigSelect.appendChild(teleopOption);
        });

    } catch (error) {
        console.error("Error fetching robot configs:", error);
    }
});

document.addEventListener("DOMContentLoaded", async () => {
    const container = document.getElementById("cameraContainer");

    try {
        // Fetch the list of cameras from the backend
        const response = await fetch("/robot/cameras");
        const cameras = await response.json();

        container.innerHTML = "";
        // Populate the container with cards
        cameras.forEach(camera => {
            // Create the card div
            const card = document.createElement("div");
            card.className = "card m-4";
            // card.style.marginBottom = "20px";
            // card.style.width = "480px";
            // card.style.height = "240px";
            card.style.width = "320px";

            // Create the card body
            const cardBody = document.createElement("div");
            cardBody.className = "card-body p-2";

            // Add camera name as a paragraph
            const cardText = document.createElement("p");
            cardText.className = "card-text";
            cardText.textContent = camera.name;
            cardBody.appendChild(cardText);

            // Add the video/image element
            const cardImg = document.createElement("img");
            cardImg.className = "card-img-bottom";
            cardImg.alt = camera.name;
            // cardImg.style.width = "480px";
            // cardImg.style.height = "240px";

            cardImg.style.width = "320px";
            cardImg.style.height = "240px";
            cardImg.style.background = "#000";
            cardImg.style.borderRadius = "4px";

            // Set the image/video source
            cardImg.src = camera.video_url;

            // Append body and image to card
            card.appendChild(cardBody);
            card.appendChild(cardImg);

            // Append card to the container
            container.appendChild(card);
        });
    } catch (error) {
        console.error("Error fetching camera data:", error);
    }
});

document
    .getElementById("startTeleopBtn")
    .addEventListener("click", async () => {
    try {
        await fetch("/select_mode/teleop", { method: "GET" });
        // updateStatus();
        // connectEventSource();
    } catch (error) {
        console.error("Error starting teleoperation:", error);
    }
    }); 

document
    .getElementById("stopTeleopBtn")
    .addEventListener("click", async () => {
    try {
        await fetch("/stop", { method: "GET" });
    } catch (error) {
        console.error("Error stopping teleoperation:", error);
    }
    });

document
    .getElementById("startRecordSessionBtn")
    .addEventListener("click", async () => {
    try {
        await fetch("/select_mode/record", { method: "GET" });
        // updateStatus();
        // connectEventSource();
    } catch (error) {
        console.error("Error starting teleoperation:", error);
    }
    });

document
    .getElementById("stopRecordSessionBtn")
    .addEventListener("click", async () => {
    try {
        await fetch("/stop", { method: "GET" });
        // updateStatus();
        // if (window.eventSource) {
        //   window.eventSource.close();
        // }
    } catch (error) {
        console.error("Error stopping teleoperation:", error);
    }
    });

// start editing here
document
    .getElementById("startRecordBtn")
    .addEventListener("click", async () => {
    try {
        await fetch("/record/start_recording", { method: "GET" });
    } catch (error) {
        console.error("Error starting recording:", error);
    }
    });

document
    .getElementById("finishRecordBtn")
    .addEventListener("click", async () => {
    try {
        await fetch("/record/finish_recording", { method: "GET" });
    } catch (error) {
        console.error("Error finishing recording:", error);
    }
    });

document
    .getElementById("cancelRecordBtn")
    .addEventListener("click", async () => {
    try {
        await fetch("/record/cancel_recording", { method: "GET" });
    } catch (error) {
        console.error("Error cancelling recording:", error);
    }
    });

    const teleopConfigForm = document.getElementById('teleopConfigForm');
    teleopConfigForm.addEventListener('submit', async (event) => {
        console.log("sending teleop config form");
        event.preventDefault(); // Prevent the default form submission
        const formData = new FormData(teleopConfigForm);
        console.log(formData);
        const response = await fetch(teleopConfigForm.action, {
            method: teleopConfigForm.method,
            body: formData
        });
        if (response.ok) {
            alert('Configuration Updated Successfully!');
        } else {
            alert('Error updating configuration!');
        }
    });

    const recordConfigForm = document.getElementById('recordConfigForm');
    recordConfigForm.addEventListener('submit', async (event) => {
        console.log("sending record config form");
        event.preventDefault(); // Prevent the default form submission
        const formData = new FormData(recordConfigForm);
        const response = await fetch(recordConfigForm.action, {
            method: recordConfigForm.method,
            body: formData
        });
        if (response.ok) {
            alert('Configuration Updated Successfully!');
        } else {
            alert('Error updating configuration!');
        }
    });

    document.addEventListener("DOMContentLoaded", async () => {
    const form = document.getElementById("recordConfigForm");

    try {
        // Fetch data from the backend
        const response = await fetch("/record/get-config");
        const data = await response.json();

        // Map backend data to form fields
        form.robotConfigSelect.value = data.robot_config;
        form.recordRoot.value = data.root;
        form.recordRepoID.value = data.repo_id;
        form.recordTags.value = data.tags;
        form.recordFPS.value = data.fps;

        // Handle switches
        form.resumeRecordToggle.checked = data.resume;
        form.recordLocalFilesToggle.checked = data.local_files_only;
        form.recordRunComputeStats.checked = data.run_compute_stats;
        form.recordPushToHub.checked = data.push_to_hub;

        // Handle time and episode inputs
        form.recordEpisodeTime.value = data.episode_time_s;
        form.recordNumEpisodes.value = data.num_episodes;

        // Handle image writer settings
        form.recordImageWriterProcesses.value = data.num_image_writer_processes;
        form.recordImageWriterThreads.value = data.num_image_writer_threads_per_camera;
        form.recordSingleTask.value = data.single_task;

    } catch (error) {
        console.error("Error fetching configuration data:", error);
    }
});

    function startStreaming() {
    const eventSource = new EventSource("/stream");
    const logsDisplay = document.getElementById("logsDisplay");

    eventSource.onmessage = function(event) {

        console.log(event.data);

        const newLine = document.createElement("div");
        newLine.textContent = event.data;

        logsDisplay.appendChild(newLine);
        logsDisplay.scrollTop = logsDisplay.scrollHeight;

        if (event.data === "--- Streaming ended ---") {
            eventSource.close();
        }
    };

    eventSource.onerror = function() {
        console.log("Error occurred while streaming.");
        eventSource.close();
    };
    }

//   document
//     .getElementById("recordButton")
//     .addEventListener("click", async () => {
//       try {
//         output.innerHTML = "";
//         const response = await fetch("/recording/start", {
//           method: "POST",
//         });
//         const data = await response.json();
//         console.log("Started recording:", data.recording_id);
//         updateStatus();
//         connectEventSource();
//       } catch (error) {
//         console.error("Error starting recording:", error);
//       }
//     });

//   async function replayRecording(recordingId) {
//     try {
//       output.innerHTML = "";
//       const response = await fetch(`/replay/${recordingId}`, {
//         method: "POST",
//       });
//       const data = await response.json();
//       console.log("Started replay:", data.message);
//       updateStatus();
//       connectEventSource();
//     } catch (error) {
//       console.error("Error starting replay:", error);
//     }
//   }

//   async function updateRecordings() {
//     try {
//       const response = await fetch("/recordings");
//       const recordings = await response.json();
//       const listElement = document.getElementById("recordings");

//       let html = "<h3>Available Recordings</h3>";
//       recordings.forEach((recording) => {
//         const date = new Date(recording.created * 1000).toLocaleString();
//         html += `
//           <div class="recording-item">
//             <div class="recording-info">
//               <strong>${recording.id}</strong><br>
//               <small>Created: ${date}</small>
//             </div>
//             <button class="button replay-btn" onclick="replayRecording('${recording.id}')">
//               Replay
//             </button>
//           </div>
//         `;
//       });

//       listElement.innerHTML = html;
//     } catch (error) {
//       console.error("Error fetching recordings:", error);
//     }
//   }

// Only check status periodically, remove initial EventSource connection
//   updateStatus();
//   setInterval(updateStatus, 2000);
//   updateRecordings();
//   setInterval(updateRecordings, 5000);

startStreaming();