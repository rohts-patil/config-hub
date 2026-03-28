# Config-Hub Documentation

Welcome to the **Config-Hub** platform documentation! This guide showcases the core features provided by our feature flag and configuration management dashboard. 

Below you will find a visual walkthrough of the main capabilities, complete with screenshots of the actual interface.

> **Tip:** Navigating the platform is easy. You can switch between different organizations and products using the selectors in the top header, and use the left sidebar to dive into specific features.

---

## 1. Organizations and Products Management

Config-Hub is built for multi-tenancy. You can create multiple organizations to isolate users and billing, and within each organization, you can define multiple products.

![Organizations Overview](./images/organizations_page_1774698506278.png)
![Products Dashboard](./images/products_page_empty_1774698573146.png)
![Organization Selector](./images/organization_selector_dropdown_1774699327223.png)
![Product Selector](./images/product_selector_dropdown_1774699375966.png)

---

## 2. Feature Management

At the heart of Config-Hub are the configurations (feature flags). Here you can define individual flags, control their rollout states, and group them with tags.

### Configs
Manage your individual feature flags and dynamic configurations.
*To create a new one, click the **New Config** button and define its key and settings.*

![Configs Dashboard](./images/configs_page_empty_1774698649583.png)
![Create Config Modal](./images/create_config_modal_1774698983556.png)

### Environments
Isolate configurations across different deployment stages (e.g., Development, Staging, Production). Each environment has its own independent state for feature flags.

![Environments Dashboard](./images/environments_page_empty_1774698674311.png)
![Create Environment Modal](./images/create_environment_modal_1774699066654.png)

### Segments and Tags
- **Segments:** Target specific groups of users based on custom attributes (e.g., "Beta Users", "Premium Subscribers").
- **Tags:** Categorize and filter your configurations for easier management.

![Segments Dashboard](./images/segments_page_empty_1774698702811.png)
![Create Segment Modal](./images/create_segment_modal_1774699161359.png)
![Tags Dashboard](./images/tags_page_empty_1774698733901.png)

---

## 3. Developer Tools and Integrations

Integrate Config-Hub into your applications and monitor system activity.

### SDK Keys
Generate unique SDK keys for your different environments to securely connect your applications to Config-Hub.

![SDK Keys](./images/sdk_keys_page_empty_1774698765069.png)

### Audit Logs
Track every change made within your organization. Audit logs provide a comprehensive history of who changed what, and when, ensuring full compliance and traceability.

![Audit Logs](./images/audit_log_page_1774698820155.png)

### Webhooks
Set up webhooks to receive real-time notifications about events happening within your Config-Hub environment (e.g., when a feature flag is toggled or updated).

![Webhooks](./images/webhooks_page_empty_1774698862848.png)

---

## 4. User Profile

Manage your personal settings, password, and session directly from the profile dropdown located at the top right corner.

![User Profile](./images/user_profile_menu_1774699281743.png)

---

## Full Dashboard Walkthrough

> **Note:** Below is a recorded video of the interface exploration covering all these primary features from start to finish.

![Dashboard Walkthrough Video](./images/dashboard_features_1774698421862.webp)
