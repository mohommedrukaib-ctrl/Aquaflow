import { createRoot } from "react-dom/client";
import CustomerListPage from "./CustomerListPage.jsx";

const rootElement = document.getElementById("customer-react-root");
const dataElement = document.getElementById("customer-page-data");

if (rootElement && dataElement) {
  try {
    const data = JSON.parse(dataElement.textContent);

    const csrfToken =
      document.querySelector(
        "#customer-csrf-form input[name='csrfmiddlewaretoken']"
      )?.value || "";

    createRoot(rootElement).render(
      <CustomerListPage data={data} csrfToken={csrfToken} />
    );
  } catch (error) {
    console.error("Could not load the Customers page:", error);

    rootElement.innerHTML = `
      <div class="alert alert-danger">
        The Customers page could not be loaded.
      </div>
    `;
  }
}