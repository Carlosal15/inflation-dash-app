# docker build command
docker build -t inflation-dash-app .          

# docker run command (careful with the -rm flag as I may need the logs if it fails)
docker run -p 8080:8080 --rm   -d --name docker-dash-app inflation-dash-app
