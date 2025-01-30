// js for common app funcs

// enable tooltips
const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
tooltipTriggerList.forEach(t => {
    new bootstrap.Tooltip(t);
})

document.addEventListener("DOMContentLoaded", async () => {

    const teleopRobotConfigForm = document.getElementById("teleopConfigForm");
    const teleopRobotConfigSelect = teleopRobotConfigForm.querySelector("#robotConfigSelect");

    const recordRobotConfigForm = document.getElementById("recordConfigForm");
    const recordRobotConfigSelect = recordRobotConfigForm.querySelector("#robotConfigSelect");

    const evalRobotConfigForm = document.getElementById("evalConfigForm");
    const evalRobotConfigSelect = evalRobotConfigForm.querySelector("#robotConfigSelect");

    const HGDAggerConfigForm = document.getElementById("HGDAggerConfigForm");
    const HGDAggerRobotConfigSelect = HGDAggerConfigForm.querySelector("#robotConfigSelect");

    try {
        // fetch the list of cameras from the backend
        const response = await fetch("/robot/configs-path");
        const configsPath = await response.json();

        // clear existing options
        recordRobotConfigSelect.innerHTML = "";
        teleopRobotConfigSelect.innerHTML = "";
        evalRobotConfigSelect.innerHTML = "";
        HGDAggerRobotConfigSelect.innerHTML = "";

        // populate the <select> element with options
        configsPath.forEach(path => {
            const recordOption = document.createElement("option");
            recordOption.value = path;
            recordOption.textContent = path;
            recordRobotConfigSelect.appendChild(recordOption);

            const teleopOption = document.createElement("option");
            teleopOption.value = path;
            teleopOption.textContent = path;
            teleopRobotConfigSelect.appendChild(teleopOption);

            const evalOption = document.createElement("option");
            evalOption.value = path;
            evalOption.textContent = path;
            evalRobotConfigSelect.appendChild(evalOption);

            const HGDAggerOption = document.createElement("option");
            HGDAggerOption.value = path;
            HGDAggerOption.textContent = path;
            HGDAggerRobotConfigSelect.appendChild(HGDAggerOption);
        });

    } catch (error) {
        console.error("Error fetching robot configs:", error);
    }
});

document.addEventListener("DOMContentLoaded", async () => {
    const container = document.getElementById("cameraContainer");

    try {
        // fetch the list of cameras from the backend
        const response = await fetch("/robot/cameras");
        const cameras = await response.json();

        container.innerHTML = "";
        // populate the container with cards
        cameras.forEach(camera => {
            const card = document.createElement("div");
            card.className = "card m-4";
            card.style.width = "320px";
            card.style.height = "280px";
            card.style.overflow = "hidden";

            // card body
            const cardBody = document.createElement("div");
            cardBody.className = "card-body p-2";
            cardBody.style.backgroundColor = "var(--bs-gray-800)!important";
            
            const cardText = document.createElement("p");
            cardText.className = "card-text";
            cardText.textContent = camera.name;
            cardText.style.fontStyle = "italic";
            cardBody.appendChild(cardText);

            // add the video/image element
            const cardImg = document.createElement("img");
            cardImg.className = "card-img-bottom";
            cardImg.alt = camera.name;
            // cardImg.style.width = "320px";
            // cardImg.style.height = "240px";

            // set the image/video source
            cardImg.src = camera.video_url;

            // append body and image to card
            card.appendChild(cardBody);
            card.appendChild(cardImg);

            // append card to the container
            container.appendChild(card);
        });
    } catch (error) {
        console.error("Error fetching camera data:", error);
    }
});

function streamLogs() {
    const eventSource = new EventSource("/robot/stream-logs");
    const logsDisplay = document.getElementById("logsDisplay");

    eventSource.onmessage = function(event) {
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

// capture keyboard input
window.addEventListener("keydown", function(event) {
    const key = event.key;

    // send captured input to backend
    fetch("/api/keyboard-input", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body:  JSON.stringify({ data: key })
    })
    .then(response => response.json())
    .catch(error => {
        console.error('Error sending keyboard input to backend:', error);
    });
});

// reset robot
document.getElementById("resetRobotBtn")
.addEventListener("click", function() {

    fetch("/api/reinit-robot", {
        method: "GET",
    })
    .then(response => response.json())
    .catch(error => {
        console.error('Error reinitializing robot on backend:', error);
    });
});

// start async funcs
streamLogs();