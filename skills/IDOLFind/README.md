<!--
BEGIN COPYRIGHT NOTICE
Copyright 2026 Open Text.

The only warranties for products and services of Open Text and its affiliates and licensors
("Open Text") are as may be set forth in the express warranty statements accompanying such
products and services. Nothing herein should be construed as constituting an additional warranty.
Open Text shall not be liable for technical or editorial errors or omissions contained herein.
The information contained herein is subject to change without notice.

END COPYRIGHT NOTICE
-->

# IDOL Find skills

Nine agent skills for standing up a *demo* of OpenText Find on Knowledge Discovery (IDOL): two to
install the IDOL components and index a dataset, one to deploy Find on top of them, and six to tailor
Find to that data and check the result.

### IDOL components

| Skill | Purpose |
|---|---|
| [`idol-component-setup`](idol-component-setup/SKILL.md) | Install, license, configure, start, verify and stop an ACI component (Content, Agentstore, Community, View, Category, QMS and others) from its product zip, on Linux or Windows, as a process or a service. Reference material under [`idol-component-setup/reference/`](idol-component-setup/reference). |
| [`idol-index`](idol-index/SKILL.md) | Get an IDX dataset into Content well - profile its fields, choose field types, clean awkward values, load, reindex and verify with queries and parametric values. |

### OpenText Find

| Skill | Purpose |
|---|---|
| [`find-setup`](find-setup/SKILL.md) | Deploy `find.war` on top of the IDOL components, wire it to Content, Community and View, and set up the FindUser/FindBI/FindAdmin roles and users. |
| [`find-customize`](find-customize/SKILL.md) | The starting point for broad "tailor Find to this data" requests: which of the skills below does what, and in which order. |
| [`find-fields-and-filters`](find-fields-and-filters/SKILL.md) | Friendly field names, the filter sidebar, sort options, result tabs per role and the message of the day, all in Find's `config.json`. |
| [`find-result-templates`](find-result-templates/SKILL.md) | Result cards and the preview panel as Handlebars templates, such as a product card with price and rating, or image thumbnails. |
| [`find-dashboard`](find-dashboard/SKILL.md) | Dashboards, their widgets and layout, and the saved searches behind them. |
| [`find-branding`](find-branding/SKILL.md) | Logos, search-term highlight colours and the message of the day. |
| [`find-ui-check`](find-ui-check/SKILL.md) | Log in as a given user in a browser and check what Find actually shows them - screenshots, console errors, failed API calls and page content. |

Each skill is a directory holding a `SKILL.md` and any files it references. The skills name each
other where one hands over to another, so install them as a set.

## Usage

Describe what you want and the agent should pick the right skill, or name one directly
(`/find-setup`, `/find-customize`, `/idol-index`). For example:

> Set up Content, Community, an Agentstore and View from the zips in `~/idol`, then deploy Find on
> top of them. My licence server is `licences.example.com` port 20000.

> Index `products.idx` into a new `products` database. Price and rating should be numeric, and
> brand, colour and category should be filters.

> Make Find good for this product catalogue: friendly field names, sensible filters, sorting by price
> and rating, and product cards with a thumbnail.

> Add a dashboard showing products by category and brand, and check a FindBI user can see it.

## What they expect of you

- **The product zips and a License Server.** `idol-component-setup` works from the published
  `<Component>_<ver>_<OS>_<ARCH>.zip` files - Content, Community and View for Find, and Find itself -
  and needs the `host:port` of a License Server with licences for them. It will ask for anything it
  cannot find rather than skip a component.
- **Java 17**, to run `find.war`.
- **Data in IDX form**, for `idol-index`, and a running Find with that data in Content for the
  `find-*` customisation skills. If you are starting from nothing, work through the skills in the
  order of the tables above.
- **A browser the agent can drive**, for `find-ui-check` - a browser tool, Playwright or Puppeteer,
  or headless Chrome over the DevTools protocol.
- **Decisions.** Which fields become filters, how results should look and what a dashboard should
  show are your call; the skills propose, and `find-ui-check` shows you the outcome as each role sees
  it.

## Before you use them

These skills build demos, not production systems.

- **Credentials.** The skills generate random passwords, keep them in a `chmod 600` file and try not
  to print them, but as with any LLM-based agent, mistakes can happen. Change or revoke the
  passwords once your demo is configured.
- **Security.** The skills make no attempt to secure the deployment. Follow the product
  documentation to do that.
- **Your data.** `idol-index` and the customisation skills read the documents you index in order to
  profile fields and choose filters and templates. **Do not use them with sensitive data**, as it may
  be sent to the agent's model provider.
