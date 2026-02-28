# Issue Analysis - What Went Wrong

## Summary
The application actually **succeeded** in the final run (lines 620-652 in backend logs), but there were several issues that caused problems earlier:

## Issues Identified

### 1. **In-Memory Storage (Critical)**
**Problem**: All data is stored in Python dictionaries in memory:
- `questions_store` - stores uploaded questions
- `process_statuses` - tracks processing progress
- `visualizations_store` - stores generated visualizations

**Impact**: 
- When the backend server restarts, **all data is lost**
- Questions become "not found" after restarts (lines 250, 256, 419-420, 422-423)
- Process IDs become invalid after restarts
- This is why you see "Question not found" errors after server restarts

**Evidence from logs**:
```
18:01:13 | WARNING  | Question not found: be71e3a7-af85-45da-b66a-80fbce49c5a9
18:02:44 | WARNING  | Question not found: dff81407-b059-49d7-aca7-8f41b923c741
```

### 2. **API Key Management**
**Problem**: 
- Initially had invalid OpenAI API key
- User exported key in terminal: `export OPENAI_API_KEY=...` (line 228, 563)
- This is **not persistent** - key is lost when terminal closes

**Impact**:
- API calls fail with 401 errors when key is missing/invalid
- Need to re-export key every time server restarts

**Solution**: Create `.env` file in `backend/` directory with:
```env
OPENAI_API_KEY=your_key_here
```

### 3. **Frontend Proxy Connection Issues**
**Problem**: 
- Frontend uses Next.js rewrites to proxy `/api/*` → `http://localhost:8000/api/*`
- "Socket hang up" errors occur when:
  - Backend restarts (due to code changes with `--reload`)
  - Backend crashes during processing
  - Network timeout

**Evidence from logs**:
```
Failed to proxy http://localhost:8000/api/process/fe5c9f48-63f0-44fe-b340-dd49dfa48b36 
Error: socket hang up
```

**Impact**:
- Frontend loses connection to backend during processing
- Progress polling fails
- User sees errors even though backend might be working

### 4. **Server Restarts During Development**
**Problem**: 
- Backend uses `--reload` flag which restarts on code changes
- Multiple restarts visible in logs (lines 130-227, 395-227, etc.)
- Each restart loses all in-memory data

**Impact**:
- Questions uploaded before restart are lost
- Process IDs become invalid
- Frontend polling fails because process_id no longer exists

### 5. **Progress Polling Error Handling**
**Problem**: 
- Frontend polls every 2 seconds for progress
- After 5 consecutive errors, it stops polling (line 127 in preview/page.tsx)
- Doesn't handle backend restarts gracefully

**Impact**:
- If backend restarts during processing, frontend gives up after 10 seconds
- User sees error even if backend is working again

## What Actually Worked

The **final run was successful** (lines 620-652):
1. ✅ Question uploaded successfully
2. ✅ Question analysis completed (Type: coding, Subject: Data Structures and Algorithms)
3. ✅ Story generated successfully ("The Fusion of Crystal Streams")
4. ✅ HTML visualization generated (2060 characters)
5. ✅ Pipeline completed successfully
6. ✅ Visualization stored with ID: `ec1fe1df-d422-4439-a004-76a4dc397edb`

## Root Causes

1. **No persistent storage** - Everything in memory
2. **API key not in .env file** - Must be exported manually
3. **Development server restarts** - Loses all data
4. **Frontend doesn't handle backend restarts** - Gives up too quickly

## Recommendations

### Immediate Fixes:
1. **Create `.env` file** in `backend/` directory with API key
2. **Add better error handling** in frontend for connection issues
3. **Add retry logic** for progress polling

### Long-term Fixes:
1. **Add database** (SQLite for dev, PostgreSQL for prod) instead of in-memory storage
2. **Add health check endpoint** for frontend to detect backend availability
3. **Add connection retry logic** in frontend
4. **Consider using Redis** for process status tracking (survives restarts)

## Next Steps

1. Create `.env` file with valid API key
2. Test the successful flow (it worked in the last run!)
3. Consider adding persistent storage for production use
4. Improve frontend error handling and retry logic


