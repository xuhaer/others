SELECT 	TOP(4000) xx.testId AS testId, xx.sampleTypeId, xx.value, xx.unit
FROM(
    SELECT * 
    FROM (
        SELECT  
            ROW_NUMBER() OVER (PARTITION BY t.testId, t.userId, s.sampleTypeId ORDER BY t.testId) AS RowNum,
            t.testId AS testId, t.userId AS userId,
            s.sampleId, s.sampleTypeId, s.value,s.unit
        FROM HMP3.dbo.T_Test AS t
        JOIN HMP3.dbo.T_Correlation AS c
        ON t.userId = c.userId AND t.testId = c.testId
        JOIN HMP3.dbo.T_Sample AS s
        ON s.userId = t.userId
        WHERE s.sampleTypeId IN (159, 160, 162, 144, 145, 3, 5, 4, 2)) AS res
    WHERE RowNum = 1
	) AS xx
JOIN HMP3.dbo.T_PA_UserRecord AS u 
ON u.userId = xx.userId
WHERE YEAR(u.birthday) = {dob} AND gender = {gender};