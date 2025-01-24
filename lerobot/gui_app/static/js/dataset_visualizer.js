// js for dataset visualizer

document.addEventListener("DOMContentLoaded", async () => {
    const container = document.getElementById("videoContainer");

    try {
        // fetch the list of cameras from the backend
        const response = await fetch("/dataset/get-video-info");
        const videos = await response.json();

        container.innerHTML = "";
        // populate the container with cards
        videos.forEach(video => {
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
            cardText.textContent = video.name;
            cardText.style.fontStyle = "italic";
            cardBody.appendChild(cardText);

            // add the video/image element
            const cardImg = document.createElement("img");
            cardImg.className = "card-img-bottom";
            cardImg.alt = video.name;
            // cardImg.style.width = "320px";
            // cardImg.style.height = "240px";

            // set the image/video source
            cardImg.src = video.video_url;

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

document.addEventListener('DOMContentLoaded', function() {
    fetch('/dataset/get-dataset-info')
        .then(response => response.json())
        .then(data => {
            console.log(data);
            document.querySelector('#datasetInfoDisplay h6:nth-child(1)').textContent = `RepoID: ${data.repo_id}`;
            document.querySelector('#datasetInfoDisplay h6:nth-child(2)').textContent = `Number of episodes: ${data.num_episodes}`;
            document.querySelector('#datasetInfoDisplay h6:nth-child(3)').textContent = `Number of samples: ${data.num_samples}`;
            document.querySelector('#datasetInfoDisplay h6:nth-child(4)').textContent = `Frames per second: ${data.fps}`;

            const selectElement = document.getElementById('datasetEpisodeSelect');
            selectElement.innerHTML = ''; // Clear existing options

            for (let i = 0; i < data.num_episodes; i++) {
                const option = document.createElement('option');
                option.value = i;
                option.textContent = `Episode ${i}`;
                selectElement.appendChild(option);
            }


            // Add event listener for change event
            selectElement.addEventListener('change', function() {
                const selectedEpisode = selectElement.value;
                console.log("episode changed", selectedEpisode);
                fetch(`/dataset/change-episode/${selectedEpisode}`)
                    .then(response => response.json())
                    .then(episodeData => {
                        console.log(episodeData);
                        // Handle the episode data as needed
                    })
                    .catch(error => console.error('Error fetching episode info:', error));
            });
        })
        .catch(error => console.error('Error fetching dataset info:', error));
});

function streamStateAction() {
    const eventSource = new EventSource('/dataset/get-state-action');
    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        const tbody = document.getElementById('stateActionDisplayTable');
        tbody.innerHTML = ''; // Clear existing rows

        data.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${item.joint}</td>
                <td>${item.state}</td>
                <td>${item.action}</td>
            `;
            tbody.appendChild(row);
        });
    };
}

streamStateAction();
