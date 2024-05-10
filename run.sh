#!/bin/bash


SCRIPT_PATH=$(readlink -f "$0")
DIR_PATH=$(dirname "$SCRIPT_PATH")

INFO_MARK="-->"
SUCCESS_MARK="[\033[32mV\033[0m]"
FAILURE_MARK="[\033[31mX\033[0m]"
QUESTION_MARK="[\033[33m?\033[0m]"

INFO() {
    echo -e "$INFO_MARK $1"
}

SUCCESS() {
    echo -e "$SUCCESS_MARK $1"
}

FAILURE() {
    echo -e "$FAILURE_MARK $1"
}

QUESTION() {
    echo -e "$QUESTION_MARK $1"
}

# Активация виртуального окружения

INFO "Searching python virtual environment"
if [[ -f "$DIR_PATH/venv/bin/activate" ]]; then
    INFO "Trying to activate python virtual environment"
    if source "$DIR_PATH/venv/bin/activate"; then
        SUCCESS "Python virtual environment activated successfully"
    else
        FAILURE "Python virtual environment cannot be activated for some reason"
        exit 1
    fi
else
    FAILURE "Python virtual environment was not found"
    INFO "Trying to create new virtual environment"

    if /usr/bin/python3 -m venv "$DIR_PATH/venv"; then
        SUCCESS "Pyhton virtual environment was created successfully"

        INFO "Trying to activate python virtual environment"
        if source "$DIR_PATH/venv/bin/activate"; then
            SUCCESS "Python virtual environment activated successfully"
        else
            FAILURE "Python virtual environment cannot be activated for some reason"
            exit 1
        fi
    else
        FAILURE "Python virtual environment was not created for some reason"
        QUESTION "Do you have python3 installed on your machine?"
        exit 2
    fi
fi


# Проверка наличия необходимых модулей

INFO "Checking installed modules"

required_modules_in_list=(
    "requests"
    "PyQt6"
    "beautifulsoup4"
    "termcolor"
)

required_modules=(
    "requests"
    "pyqt6"
    "beautifulsoup4"
    "termcolor"
)

pip_path="$DIR_PATH/venv/bin/pip"
pip_list=$(echo "$($pip_path list)")
not_installed_modules=()

indexes="$(seq -s " " 0 $(( ${#required_modules_in_list[@]}-1 )) )"

for module_id in $indexes; do
    if echo "$pip_list" | grep -q "${required_modules_in_list[$module_id]}"; then
        SUCCESS "\`${required_modules_in_list[$module_id]}\` is installed"
    else
        FAILURE "\`${required_modules_in_list[$module_id]}\` is not installed"
        not_installed_modules+=("${required_modules[$module_id]}")
    fi
done

if [[ ${#not_installed_modules[@]} -gt 0 ]]; then
    QUESTION "Do you want to install required modules? [yes/(anything else)]"
    read ANSWER

    if [[ $ANSWER = "yes" ]]; then
        for module in "${not_installed_modules[@]}"; do
            if "$pip_path" install $module; then
                SUCCESS "\`$module\` was installed successfully"
            else
                FAILURE "\`$module\` was not installed"
                exit 3
            fi
        done
    else
        exit 0
    fi
fi


# Запуск программы

py_path="$DIR_PATH/venv/bin/python"

$py_path "$DIR_PATH/WebDomainCollector.py" $@


# Завершение работы виртуального окружения

INFO "Closing python virtual environment"

if deactivate; then
    SUCCESS "Python virtual environment was closed successfully"
else
    FAILURE "Python virtual environment was not closed"
fi

