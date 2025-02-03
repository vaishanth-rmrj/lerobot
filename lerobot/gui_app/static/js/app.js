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

    try {
        // fetch the list of cameras from the backend
        const response = await fetch("/robot/configs-path");
        const configsPath = await response.json();

        // clear existing options
        recordRobotConfigSelect.innerHTML = "";
        teleopRobotConfigSelect.innerHTML = "";
        evalRobotConfigSelect.innerHTML = "";

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
    fetch("/api/event/keyboard-input", {
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

    fetch("/robot/reset", {
        method: "GET",
    })
    .then(response => response.json())
    .catch(error => {
        console.error('Error reinitializing robot on backend:', error);
    });
});

// home robot
document.getElementById("homeRobotBtn")
.addEventListener("click", function() {

    fetch("/api/home-robot", {
        method: "GET",
    })
    .then(response => response.json())
    .catch(error => {
        console.error('Error homing robot on backend:', error);
    });
});

// activate events
async function activateEvent(event_name) {
    try {
        const response = await fetch('/api/event/activate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ event: event_name })
        });
        const data = await response.json();
        if (data.status === "success") {
            return true;
        } else {
            return false;
        }
    } catch (error) {
        console.error(`Error activating event -> ${event_name}:`, error);
    }
}

// stream state and action
function streamStateAction() {
    const eventSource = new EventSource('/robot/stream-state-action');
  
    eventSource.onmessage = function(event) {
      // Parse the response; it is expected to be an array of objects,
      // each with properties: joint, state, and action.
      const data = JSON.parse(event.data);
  
      const table_body = document.getElementById('stateActionDisplayTable');      
      // Check if the table already exists
      let is_table_populated = table_body.querySelector('tr');
  
      if (!is_table_populated) {
  
        data.forEach(item => {
          const row = document.createElement('tr');
  
          // Joint Name cell (provided by the response).
          const tdJoint = document.createElement('td');
          tdJoint.textContent = item.joint;
          row.appendChild(tdJoint);
  
          // State cell.
          const tdState = document.createElement('td');
          tdState.textContent = item.state;
          row.appendChild(tdState);
  
          // Action cell.
          const tdAction = document.createElement('td');
          tdAction.textContent = item.action;
          row.appendChild(tdAction);
  
          table_body.appendChild(row);
        });

      } else {
        // The table already exists, so update the state and action columns.
        const rows = table_body.querySelectorAll('tr');
        data.forEach((item, index) => {
          if (rows[index]) {
            // Update the state cell (cell index 1) and action cell (cell index 2)
            rows[index].cells[1].textContent = parseFloat(item.state).toFixed(2);
            rows[index].cells[2].textContent = parseFloat(item.action).toFixed(2);
          }
        });
      }
    };
  
    eventSource.onerror = function(error) {
      console.error("Error with EventSource:", error);
    };
}

// start async funcs
streamStateAction();
streamLogs();