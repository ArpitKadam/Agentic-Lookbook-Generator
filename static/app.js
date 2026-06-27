function addUrlField() {

    const container =
        document.getElementById("url-container");

    const input =
        document.createElement("input");

    input.type = "text";

    input.placeholder =
        "https://example.com/image.jpg";

    input.className = "url-input";

    container.appendChild(input);
}


async function generateLookbook() {

    const theme =
        document.getElementById("theme").value;

    const urls =
        Array.from(
            document.querySelectorAll(".url-input")
        )
        .map(input => input.value)
        .filter(url => url !== "");

    if (!theme || urls.length === 0) {

        alert("Provide theme and image URLs.");

        return;
    }

    document.getElementById("loading").innerHTML =
        "<p>Generating Lookbook... Please wait.</p>";

    document.getElementById("results").innerHTML = "";

    try {

        const response = await fetch(
            "/generate",
            {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    theme_prompt: theme,

                    image_urls: urls

                })
            }
        );

        const data = await response.json();

        displayResults(data);

    }

    catch (error) {

        console.error(error);

        alert("Something went wrong.");
    }

    document.getElementById("loading").innerHTML = "";
}


function displayResults(data) {

    const container =
        document.getElementById("results");

    container.innerHTML = "";

    const title = document.createElement("h2");

    title.innerText =
        data.lookbook.edition_title;

    container.appendChild(title);

    data.lookbook.collection.forEach(card => {

        const div =
            document.createElement("div");

        div.className = "lookbook-card";

        div.innerHTML = `

            <h3>
                ${card.card_number}
                •
                ${card.mood_title}
            </h3>

            <p>
                <strong>Brand:</strong>
                ${card.brand_or_designer}
            </p>

            <p>
                <strong>Product:</strong>
                ${card.product_type}
            </p>

            <p>
                <strong>Tags:</strong>
                ${card.sub_tags.join(" • ")}
            </p>

            <p>
                ${card.vibe_description}
            </p>

        `;

        container.appendChild(div);
    });

    const metrics =
        document.createElement("div");

    metrics.className = "lookbook-card";

    metrics.innerHTML = `

        <h3>Pipeline Metrics</h3>

        <p>
            Total Tokens Used:
            ${data.total_tokens}
        </p>

    `;

    container.appendChild(metrics);
}