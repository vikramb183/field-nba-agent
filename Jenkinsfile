// Same pipeline as .github/workflows/ci.yml, for teams that run Jenkins.
pipeline {
    agent any

    stages {
        stage('Install') {
            steps {
                sh 'python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt'
            }
        }
        stage('Test') {
            steps {
                sh '. .venv/bin/activate && mkdir -p reports && pytest --junitxml=reports/junit.xml'
            }
        }
        stage('Docker build') {
            steps {
                sh 'docker build -t field-nba-agent:${BUILD_NUMBER} .'
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'reports/junit.xml'
        }
    }
}
