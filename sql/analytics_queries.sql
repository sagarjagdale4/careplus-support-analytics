
-- ==========================================
-- CarePlus Support Analytics
-- SQL Analytics Queries
-- ==========================================


-- ==========================================
-- 1. Ticket Count by Channel
-- ==========================================

SELECT
    channel,
    COUNT(*) AS ticket_count
FROM support_tickets
GROUP BY channel
ORDER BY ticket_count DESC;


-- ==========================================
-- 2. Ticket Status Summary
-- ==========================================

SELECT
    COUNT(*) AS total_tickets,

    SUM(
        CASE
            WHEN status = 'Resolved' THEN 1
            ELSE 0
        END
    ) AS resolved_tickets,

    SUM(
        CASE
            WHEN status = 'Open' THEN 1
            ELSE 0
        END
    ) AS open_tickets,

    SUM(
        CASE
            WHEN status = 'Escalated' THEN 1
            ELSE 0
        END
    ) AS escalated_tickets

FROM support_tickets;


-- ==========================================
-- 3. System Logs by User Agent
-- ==========================================

SELECT
    user_agent,
    COUNT(*) AS event_count
FROM support_logs
GROUP BY user_agent
ORDER BY event_count DESC;


-- ==========================================
-- 4. Tickets Created by Date
-- ==========================================

SELECT
    DATE(created_at) AS day,
    COUNT(*) AS tickets_created
FROM support_tickets
GROUP BY DATE(created_at)
ORDER BY day;


-- ==========================================
-- 5. Debug Log Count
-- ==========================================

SELECT
    COUNT(*) AS debug_event_count
FROM support_logs
WHERE log_level = 'DEBUG';


-- ==========================================
-- 6. Average CPU Usage by User Agent
-- ==========================================

SELECT
    user_agent,
    AVG(cpu) AS avg_cpu_usage
FROM support_logs
GROUP BY user_agent
ORDER BY avg_cpu_usage DESC;
