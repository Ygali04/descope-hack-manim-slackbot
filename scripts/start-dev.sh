#!/bin/bash

# ManimPro Development Startup Script
set -e

echo "🎬 Starting ManimPro Development Environment..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Please copy env.example to .env and configure your credentials:"
    echo "   cp env.example .env"
    echo "   # Edit .env with your Slack and Descope credentials"
    exit 1
fi

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found! Please install Docker and Docker Compose."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found! Please install Docker Compose."
    exit 1
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Build and start services
echo "🏗️ Building and starting services..."
docker-compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Health checks
echo "🔍 Checking service health..."

echo "Checking Slack Agent (Agent A)..."
if curl -f http://localhost:3001/health &> /dev/null; then
    echo "✅ Slack Agent is healthy"
else
    echo "❌ Slack Agent health check failed"
fi

echo "Checking Manim Agent (Agent B)..."
if curl -f http://localhost:8000/health &> /dev/null; then
    echo "✅ Manim Agent is healthy"
else
    echo "❌ Manim Agent health check failed"
fi

echo ""
echo "🎉 ManimPro is running!"
echo ""
echo "📊 Service URLs:"
echo "   Slack Agent:  http://localhost:3000 (Slack Bot)"
echo "   Manim Agent:  http://localhost:8000 (Video Renderer)"
echo "   Health Check: http://localhost:3001/health"
echo ""
echo "📋 Next Steps:"
echo "   1. Test in Slack: @ManimPro make a video on simple harmonic motion"
echo "   2. View logs: docker-compose logs -f"
echo "   3. Stop services: docker-compose down"
echo ""
echo "🔧 Development Commands:"
echo "   docker-compose logs -f slack-agent    # View Slack Agent logs"
echo "   docker-compose logs -f manim-agent    # View Manim Agent logs"
echo "   docker-compose exec slack-agent sh    # Enter Slack Agent container"
echo "   docker-compose exec manim-agent bash  # Enter Manim Agent container" 