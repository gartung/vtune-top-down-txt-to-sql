-- Useful SQL Queries for step3-29834.21.top-down.db
-- ====================================================

-- 1. Get top 20 functions by total time
SELECT full_signature, total_time, self_time, indent_level 
FROM functions 
ORDER BY total_time DESC 
LIMIT 20;

-- 2. Get top 20 functions by self time (where the function itself spends time)
SELECT full_signature, total_time, self_time, indent_level 
FROM functions 
WHERE self_time > 0
ORDER BY self_time DESC 
LIMIT 20;

-- 3. Get immediate children of a specific function (e.g., doEvent)
SELECT f.short_name, f.total_time, f.self_time, f.full_signature
FROM functions f 
JOIN call_relationships cr ON f.id = cr.child_id 
JOIN functions p ON cr.parent_id = p.id 
WHERE p.short_name LIKE '%EDProducerAdaptorBase::doEvent%' 
ORDER BY f.total_time DESC;

-- 4. Count functions at each indent level
SELECT indent_level, COUNT(*) as count, 
       SUM(total_time) as total_time_sum,
       SUM(self_time) as self_time_sum
FROM functions 
GROUP BY indent_level 
ORDER BY indent_level;

-- 5. Find all callers of a specific function
SELECT p.short_name as parent, p.total_time as parent_total_time,
       c.short_name as child, c.total_time as child_total_time
FROM call_relationships cr
JOIN functions p ON cr.parent_id = p.id
JOIN functions c ON cr.child_id = c.id
WHERE c.short_name LIKE '%malloc%'
LIMIT 50;

-- 6. Get root level functions (no parent)
SELECT f.short_name, f.total_time, f.self_time
FROM functions f
JOIN call_relationships cr ON f.id = cr.child_id
WHERE cr.parent_id IS NULL
ORDER BY f.total_time DESC;

-- 7. Find functions with highest self time percentage
SELECT full_signature, total_time, self_time, 
       ROUND(100.0 * self_time / total_time, 2) as self_percentage
FROM functions 
WHERE total_time > 0.1
ORDER BY self_percentage DESC 
LIMIT 30;

-- 8. Get all children of a specific function (recursive would need CTE)
SELECT f.short_name, f.total_time, f.self_time, f.indent_level
FROM functions f
WHERE f.indent_level > (
    SELECT indent_level FROM functions 
    WHERE short_name LIKE '%EDProducerAdaptorBase::doEvent%' 
    LIMIT 1
)
AND f.line_number > (
    SELECT line_number FROM functions 
    WHERE short_name LIKE '%EDProducerAdaptorBase::doEvent%' 
    LIMIT 1
)
LIMIT 100;

-- 9. Search for functions by name pattern
SELECT short_name, total_time, self_time, indent_level
FROM functions
WHERE short_name LIKE '%Track%' 
  AND total_time > 1.0
ORDER BY total_time DESC
LIMIT 30;

-- 10. Get statistics summary
SELECT 
    COUNT(*) as total_functions,
    MAX(total_time) as max_total_time,
    MAX(self_time) as max_self_time,
    MAX(indent_level) as max_depth,
    SUM(self_time) as total_self_time
FROM functions;

-- 11. Find functions that are called multiple times (appear at multiple lines)
SELECT short_name, COUNT(*) as occurrences, 
       SUM(total_time) as total_time_sum,
       SUM(self_time) as self_time_sum
FROM functions
GROUP BY short_name
HAVING COUNT(*) > 1
ORDER BY occurrences DESC
LIMIT 30;

-- 12. Get call chain for a specific function (limited depth)
WITH RECURSIVE call_chain(id, name, total_time, level, path) AS (
    -- Base case: start with root
    SELECT f.id, f.short_name, f.total_time, 0, f.short_name
    FROM functions f
    WHERE f.short_name = '[Unknown]'
    
    UNION ALL
    
    -- Recursive case: get children
    SELECT f.id, f.short_name, f.total_time, cc.level + 1, 
           cc.path || ' -> ' || f.short_name
    FROM call_chain cc
    JOIN call_relationships cr ON cc.id = cr.parent_id
    JOIN functions f ON cr.child_id = f.id
    WHERE cc.level < 20  -- Limit recursion depth
)
SELECT level, name, total_time, path
FROM call_chain
WHERE name LIKE '%produce%'
LIMIT 20;
