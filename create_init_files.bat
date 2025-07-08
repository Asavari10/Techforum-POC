@echo off
echo Creating __init__.py files...

REM Create main directories if they don't exist
if not exist "src" mkdir src
if not exist "src\models" mkdir src\models
if not exist "src\payment_service" mkdir src\payment_service
if not exist "src\utils" mkdir src\utils
if not exist "config" mkdir config
if not exist "tests" mkdir tests
if not exist "tests\unit" mkdir tests\unit
if not exist "tests\integration" mkdir tests\integration
if not exist "tests\generated" mkdir tests\generated
if not exist "database" mkdir database
if not exist "database\migrations" mkdir database\migrations
if not exist "database\seeds" mkdir database\seeds

REM Create __init__.py files
echo # This file makes Python treat the directory as a package > src\__init__.py
echo # This file makes Python treat the directory as a package > src\models\__init__.py
echo # This file makes Python treat the directory as a package > src\payment_service\__init__.py
echo # This file makes Python treat the directory as a package > src\utils\__init__.py
echo # This file makes Python treat the directory as a package > config\__init__.py
echo # This file makes Python treat the directory as a package > tests\__init__.py
echo # This file makes Python treat the directory as a package > tests\unit\__init__.py
echo # This file makes Python treat the directory as a package > tests\integration\__init__.py
echo # This file makes Python treat the directory as a package > tests\generated\__init__.py
echo # This file makes Python treat the directory as a package > database\__init__.py
echo # This file makes Python treat the directory as a package > database\migrations\__init__.py
echo # This file makes Python treat the directory as a package > database\seeds\__init__.py

echo.
echo Created __init__.py files in:
echo   - src\
echo   - src\models\
echo   - src\payment_service\
echo   - src\utils\
echo   - config\
echo   - tests\
echo   - tests\unit\
echo   - tests\integration\
echo   - tests\generated\
echo   - database\
echo   - database\migrations\
echo   - database\seeds\
echo.
echo All __init__.py files created successfully!