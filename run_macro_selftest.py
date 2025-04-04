import json
import os
from gpt_agent_cache import handle_command

def list_macro_test_files(folder="macro_tests"):
    test_files = []
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(".json"):
                test_files.append(os.path.join(root, file))
    return test_files

def run_all_macro_tests():
    test_files = list_macro_test_files()
    passed = 0
    failed = 0

    for path in test_files:
        print(f"\n🔍 Запуск макро: {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                test_data = json.load(f)

            steps = test_data.get("steps", [])
            cmd = {"action": "macro", "steps": steps}
            print("🔁 Кроки макроса:")
            for step in steps:
                print(step)

            result = handle_command(cmd)
            test_passed = result.get("status") == "success"

            # 🔍 Очікуване: файл
            expected_file = test_data.get("expected_file")
            if expected_file and not os.path.exists(expected_file):
                print(f"❌ Очікуваний файл '{expected_file}' не знайдено")
                test_passed = False

            # 🔍 Очікуване: код у файлі
            expected_code = test_data.get("expected_code")
            if expected_file and expected_code:
                try:
                    with open(expected_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        if expected_code not in content:
                            print(f"❌ Код не знайдено у '{expected_file}'")
                            test_passed = False
                except Exception as e:
                    print(f"❌ Помилка при читанні файлу '{expected_file}':", e)
                    test_passed = False

            # ✅ НОВА логіка — тільки RAW output
            expected_output = test_data.get("expected_output")
            if expected_output:
                raw_outputs = [r.get("output", "") for r in result.get("results", []) if isinstance(r, dict)]
                full_output = "\n".join(raw_outputs)
                print("📤 Output:", repr(full_output))
                print("🔍 Очікувано:", repr(expected_output))

                if expected_output in full_output:
                    test_passed = True
                else:
                    print(f"❌ Очікуваний результат не знайдено: '{expected_output}'")
                    test_passed = False

            if test_passed:
                print("✅ Тест пройдено")
                passed += 1
            else:
                print("❌ Тест НЕ пройдено")
                failed += 1

        except Exception as e:
            print("💥 Виняток при виконанні:", e)
            failed += 1

    print(f"\n📊 Результати: {passed} пройшло, {failed} з помилками")

if __name__ == "__main__":
    run_all_macro_tests()
