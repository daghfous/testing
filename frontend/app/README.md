# User management frontend

[![VueJS](https://img.shields.io/badge/VueJS-4FC08D?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![Sass](https://img.shields.io/badge/Sass-CC6699?logo=sass&logoColor=white)](https://sass-lang.com/)
[![Webpack](https://img.shields.io/badge/Webpack-8DD6F9?logo=webpack&logoColor=white)](https://webpack.js.org/)
[![ESLint](https://img.shields.io/badge/ESLint-4B32C3?logo=eslint&logoColor=white)](https://eslint.org/)
[![Prettier](https://img.shields.io/badge/Prettier-F7B93E?logo=prettier&logoColor=white)](https://prettier.io/)
[![Pre-commit](https://img.shields.io/badge/Pre--commit-FAB040?logo=pre-commit&logoColor=white)](https://pre-commit.com/)

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

**Table of Contents** _generated with [DocToc](https://github.com/thlorenz/doctoc)_

- [Documentation](#documentation)
- [Prerequisites](#prerequisites)
- [Build](#build)
  - [Locally](#locally)
  - [CI](#ci)
- [Usage](#usage)
  - [Dependencies install](#dependencies-install)
  - [Update dependencies](#update-dependencies)
  - [Deployment](#deployment)
    - [With local backend](#with-local-backend)
    - [With PMF backend](#with-pmf-backend)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Documentation

All reports (tests, coverage, linters, ...) are located in the `frontend/reports` directory.

## Prerequisites

**Linux**

- [Docker](https://docs.docker.com/engine/install/ubuntu/)
- [NodeJS](https://nodejs.org/) _v20.x.x_ using [NVM](https://github.com/nvm-sh/nvm)

**Windows**

- [Docker for windows](https://docs.docker.com/desktop/windows/wsl/) with [WSL2](https://docs.microsoft.com/en-us/windows/wsl/install) (choose Ubuntu 20.04 as your default distribution)
- [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- [NodeJS](https://nodejs.org/) _v20.x.x_ using [NVM](https://github.com/coreybutler/nvm-windows) for Windows

## Build

### Locally

```console
npm run build
```

### CI

The Gitlab CI pipeline will run the previous NPM script to build.

## Usage

### Dependencies install

Download and install dependencies using [npm](https://www.npmjs.com/) :

```console
npm install
```

### Update dependencies

```console
npm update
```

### Deployment

#### With local backend

1. Update `dev.env.js`:
   ```js
   module.exports = {
     USER_MANAGEMENT_URL: '"/"',
     DEPLOYING_WITH_PMF: false,
     APP_VERSION: '"3.0.0"'
   }
   ```
2. Update `config/index.js` (adapt port if needed):
   ```js
   const serverAddress = 'localhost:2529'
   const usermanagementserver = `http://${serverAddress}/`
   ```

Start frontend on localhost using:

```console
npm run dev
```

Access the web UI on [http://127.0.0.1:2525/](http://127.0.0.1:2525/)

#### With PMF backend

1. In `.env.development`, replace values with you release name.
   For instance:
   `js
  USER_MANAGEMENT_URL: "/users/",
  BASE_URL: "",
`
2. In `config/vite.config.mts`, replace "pmf-test" with your release name.
   For instance:
   `js
const serverAddress = '172.29.71.107/pmf-demo-ci'
`

3. Start frontend on localhost

   ```console
   npm run dev
   ```
