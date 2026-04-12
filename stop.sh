#!/bin/bash
echo "Stopping TrailBlaze AI servers..."
lsof -ti:8000 | xargs kill -9 2>/dev/null && \
  echo "Backend stopped." || echo "Backend was not running."
lsof -ti:3000 | xargs kill -9 2>/dev/null && \
  echo "Frontend stopped." || echo "Frontend was not running."
echo "Done."
