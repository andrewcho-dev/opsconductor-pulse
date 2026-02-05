import Keycloak from "keycloak-js";

const keycloakUrl =
  import.meta.env.VITE_KEYCLOAK_URL ||
  `${window.location.protocol}//${window.location.hostname}:8180`;

const keycloak = new Keycloak({
  url: keycloakUrl,
  realm: import.meta.env.VITE_KEYCLOAK_REALM || "pulse",
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "pulse-ui",
});

export default keycloak;
