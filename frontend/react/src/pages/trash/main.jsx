import { createRoot } from "react-dom/client";
import TrashPage from "./TrashPage.jsx";

const rootElement = document.getElementById("trash-react-root");
const dataElement = document.getElementById("trash-data");

if (rootElement && dataElement) {
  try {
    const pageData = JSON.parse(dataElement.textContent);

    const csrfToken =
      document.querySelector(
        "#trash-csrf-form input[name='csrfmiddlewaretoken']"
      )?.value || "";

    createRoot(rootElement).render(
      <TrashPage data={pageData} csrfToken={csrfToken} />
    );
  } catch (error) {
    console.error("Could not initialize the Trash React page:", error);

    rootElement.innerHTML = `
      <div class="alert alert-danger">
        The Trash page could not be loaded.
      </div>
    `;
  }
}