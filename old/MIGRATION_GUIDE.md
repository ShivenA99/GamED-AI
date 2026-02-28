# Migration Guide - Template Blueprint System

This guide helps you migrate from the old HTML-based system to the new template-based blueprint system.

## Overview of Changes

### Database Schema Changes

**New Table: `game_blueprints`**
- Stores template-specific game blueprints as JSON
- Links to questions via `question_id`
- Links to visualizations via `visualization.blueprint_id`

**Updated Table: `visualizations`**
- Added `blueprint_id` column (nullable, foreign key to `game_blueprints`)
- `html_content` is now nullable (blueprint-based visualizations don't need HTML)

### Pipeline Changes

**New Step: Template Routing (Layer 2.5)**
- Analyzes question and selects best template from 18 options
- Runs after question analysis, before strategy creation

**Updated Step: Story Generation**
- Now template-aware
- Uses `story_base.md` + template-specific supplement

**New Steps: Blueprint Generation, Asset Planning, Asset Generation**
- Replaces generic HTML generation
- Creates structured JSON blueprints
- Plans and generates required assets

### Frontend Changes

**New Components:**
- `GameEngine.tsx` - Routes to template components
- 18 template game components in `components/templates/`

**Updated Components:**
- `preview/page.tsx` - Manual "Go to Game" button (no auto-redirect)
- `game/page.tsx` - Fetches and renders blueprints via GameEngine

## Migration Steps

### 1. Backup Existing Database

```bash
cd backend
cp ai_learning_platform.db ai_learning_platform.db.backup
```

### 2. Run Database Migration

```bash
cd backend
source venv/bin/activate
PYTHONPATH=$(pwd) python scripts/migrate_add_blueprint_id.py
```

This adds the `blueprint_id` column to the `visualizations` table.

### 3. Verify Template Files

Ensure all template files exist:

**Backend Templates (18 files):**
```bash
ls backend/app/templates/*.json | wc -l  # Should be 18
```

**Story Supplements (18 files):**
```bash
ls backend/prompts/story_templates/*.txt | wc -l  # Should be 18
```

**Blueprint Interfaces (18 files):**
```bash
ls backend/prompts/blueprint_templates/*.ts.txt | wc -l  # Should be 18
```

**Frontend Components (18 files):**
```bash
ls frontend/src/components/templates/*Game.tsx | wc -l  # Should be 18
```

### 4. Update Environment Variables

No new environment variables required. Existing `.env` file works.

### 5. Restart Services

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (in new terminal)
cd frontend
npm run dev
```

### 6. Test Migration

1. Upload a new question
2. Process it through the pipeline
3. Verify template routing works
4. Check that blueprint is generated
5. Verify game renders correctly

## Backward Compatibility

The system maintains backward compatibility:

- **Old visualizations** (with HTML) still work
- API returns either `type: "html"` or `type: "blueprint"`
- Frontend handles both types
- Existing questions continue to work

## Rollback Procedure

If you need to rollback:

1. **Restore database backup**:
   ```bash
   cd backend
   cp ai_learning_platform.db.backup ai_learning_platform.db
   ```

2. **Revert code changes** (if needed):
   ```bash
   git checkout <previous-commit>
   ```

3. **Restart services**

## Data Migration

### Existing Questions

- Existing questions will continue to work
- New processing will use template system
- Old visualizations remain accessible

### Existing Visualizations

- HTML-based visualizations remain unchanged
- Can be accessed via existing API endpoints
- No data loss occurs

## Verification Checklist

After migration, verify:

- [ ] Database migration script runs without errors
- [ ] All 18 template JSON files load successfully
- [ ] Template registry initializes correctly
- [ ] New questions route to templates correctly
- [ ] Blueprints are generated and stored
- [ ] Frontend GameEngine routes correctly
- [ ] Template components render
- [ ] Old HTML visualizations still work
- [ ] API returns correct response types

## Common Issues

### Issue: "no such column: visualizations.blueprint_id"

**Solution**: Run migration script:
```bash
PYTHONPATH=$(pwd) python scripts/migrate_add_blueprint_id.py
```

### Issue: Templates not loading

**Solution**: 
- Check file paths (should be 4 levels up from pipeline services)
- Verify all 18 JSON files exist
- Check template registry logs

### Issue: Blueprint validation fails

**Solution**:
- Check blueprint matches TypeScript interface
- Verify required fields are present
- Check template metadata for required fields

### Issue: Game component not found

**Solution**:
- Verify component exists in `frontend/src/components/templates/`
- Check GameEngine switch statement includes template
- Verify TypeScript types are correct

## Post-Migration Tasks

1. **Test all 18 templates** with sample questions
2. **Verify asset generation** (currently placeholder)
3. **Implement missing template features** (many are placeholders)
4. **Add task evaluation** across all templates
5. **Enhance feedback systems**

## Support

For issues during migration:
1. Check backend logs: `backend/logs/app_*.log`
2. Check frontend console for errors
3. Verify database schema: `sqlite3 backend/ai_learning_platform.db ".schema"`
4. Review pipeline step logs via API: `/api/pipeline/steps/{process_id}`

