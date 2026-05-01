# game_scripts.py
import time
import threading
import ctypes  # [新增] 必须引入，用于底层控制线程
import inspect  # [新增] 用于检查线程状态
import dc_finger
import dc_security
import cayo_finger
import photo_climb
import ka_085
import cha_chuan_1
import cha_chuan_2
import instruction
import ka_cha_chuan
import phone_call
import mark2
#import refresh_cha_chuan_1
#mport refresh_cha_chuan_2

import  update
import  refresh_cha_chuan_jobtp2
import  fight
import sudden_stop
import ka_ceo
import key_setting
import custom_script

from concurrent.futures import ThreadPoolExecutor


class ScriptExecutor:
    # [新增] 全局变量：记录当前正在运行的那个脚本线程
    _current_thread = None
    # [新增] 线程锁：防止快速点击导致判断冲突
    _thread_lock = threading.Lock()

    # (原本的线程池可以保留，用于其他非冲突任务，或者干脆这里不用了，因为我们要手动管理线程)
    _executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="game_script")

    @staticmethod
    def open_settings_window(func_id, parent_window):
        """
        [新增] 路由分发：打开对应功能的设置界面
        (此部分代码保持不变)
        """
        print(f"[*] 请求打开设置界面: {func_id}")

        if func_id == "cha_chuan_1":
            cha_chuan_1.show_settings_ui(parent_window)
        elif func_id == "cha_chuan_2":
            cha_chuan_2.show_settings_ui(parent_window)
        elif func_id == "instruction":
            instruction.open_help_window(parent_window)
        elif func_id == "phone":
            phone_call.show_settings_ui(parent_window)
        elif func_id == "mk2":
            mark2.show_settings_ui(parent_window)
        elif func_id == "ka_cha_chuan":
            ka_cha_chuan.show_settings_ui(parent_window)

        elif func_id == "update":
            update.show_settings_ui(parent_window)
        elif func_id == "refresh_cha_chuan_bot":
            refresh_cha_chuan_jobtp2.show_settings_ui(parent_window)
        elif func_id == "fight":
            fight.show_settings_ui(parent_window)
        elif func_id == "nat_down":
            ka_085.show_settings_ui(parent_window)
        elif func_id == "sudden_stop":
            sudden_stop.show_settings_ui(parent_window)
        elif func_id == "hang_up_and_key_setting":
            key_setting.show_settings_ui(parent_window)
        elif func_id == "custom_script":
            custom_script.show_settings_ui(parent_window)



        else:
            print(f"功能 {func_id} 未配置设置界面")

    # =========================================================================
    # [核心修改] 强制结束线程的工具方法
    # =========================================================================
    @staticmethod
    def _stop_previous_thread():
        """
        检测并强制结束上一个正在运行的线程
        """
        if ScriptExecutor._current_thread is None:
            return

        thread = ScriptExecutor._current_thread
        if not thread.is_alive():
            return

        print(f"[!] 检测到旧任务 '{thread.name}' 正在运行，正在强制终止...")

        # 获取线程ID
        tid = thread.ident
        if tid is None:
            return

        # 利用 ctypes 强行向线程注入 SystemExit 异常
        # SystemExit 是 Python 内置异常，不仅会跳出循环，还会触发 finally 清理
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(tid),
            ctypes.py_object(SystemExit)
        )

        if res == 0:
            print("[x] 无法找到线程ID，可能已结束")
        elif res > 1:
            # 如果影响了多个线程（理论上不可能），回滚操作
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
            print("[x] 线程终止异常，已撤销")
        else:
            print("[V] 旧任务已终止")

        # 稍微等待一下，确保旧线程清理完毕，避免按键冲突
        time.sleep(0.1)

    # =========================================================================
    # [核心修改] 启动脚本的主入口
    # =========================================================================
    @staticmethod
    def run_script(func_id):
        """
        分发执行任务
        逻辑：先杀掉上一个，再启动这一个
        """
        # 使用锁确保 "杀旧" 和 "启新" 是原子操作
        with ScriptExecutor._thread_lock:
            # 1. 先把上一个干掉
            ScriptExecutor._stop_previous_thread()

            # 2. 创建新线程
            # 这里的 target 指向 _execute_logic
            t = threading.Thread(target=ScriptExecutor._execute_logic, args=(func_id,), name=f"Task-{func_id}")
            t.daemon = True  # 设置为守护线程，主程序关掉它也跟着关

            # 3. 记录当前线程
            ScriptExecutor._current_thread = t

            # 4. 启动
            t.start()

    @staticmethod
    def _execute_logic(func_id):
        """
        内部实际执行逻辑
        [修改] 增加了 try...except SystemExit 来捕获强制终止信号
        """
        print(f"[*] 触发脚本功能: {func_id}")

        try:
            # --- 以下是原本的业务逻辑 ---
            if func_id == "casino":
                print(">>> 执行赌场指纹破解...")
                dc_finger.run_task()

            elif func_id == "security":
                print(">>> 执行保安圆点破解...")
                dc_security.security()

            elif func_id == "cayo":
                print(">>> 执行佩岛指纹破解...")
                cayo_finger.CayoLogic.cayo_finger_run()

            elif func_id == "photo":
                print(">>> 执行拍照攀爬动作...")
                photo_climb.PhotoClimbLogic.run()

            elif func_id == "nat_down":
                print(">>> 执行断网...")
                ka_085.main()

            elif func_id == "ka_cha_chuan":
                print(">>> 执行卡差传")
                ka_cha_chuan.run_ka_cha_chuan()

            elif func_id == "cha_chuan_1":
                print(">>> 执行差传1...")
                cha_chuan_1.run()

            elif func_id == "cha_chuan_2":
                print(">>> 执行差传2...")
                cha_chuan_2.run()


            elif func_id == "refresh_cha_chuan_bot":
                print(">>> 刷新差传...")
                refresh_cha_chuan_jobtp2.refersh_manual()

            elif func_id == "sudden_stop":
                print(">>> 执行瞬间悬停...")
                sudden_stop.main()

            elif func_id == "ka_ceo":
                print(">>> 执行卡CEO...")
                ka_ceo.run_ka_ceo()

            # ----------打电话-------------
            elif func_id == "ji_gong":
                print(">>> 执行打电话: 技工")
                phone_call.ji_gong_phone()

            elif func_id == "bao_xian":
                print(">>> 执行打电话: 保险")
                phone_call.bao_xian_phone()

            elif func_id == "lester":
                print(">>> 执行打电话: 莱斯特")
                phone_call.lester_phone()

            elif func_id == "custom_1":
                print(">>> 执行打电话: 自定义1")
                phone_call.custom_1_phone()

            elif func_id == "custom_2":
                print(">>> 执行打电话: 自定义1")
                phone_call.custom_2_phone()

            elif func_id == "custom_3":
                print(">>> 执行打电话: 自定义1")
                phone_call.custom_3_phone()

            #----------马克兔-------------
            elif func_id == "call_mk2":
                print(">>> 呼叫马克兔")
                mark2.call_mk2__run()

            elif func_id == "call_sparrow":
                print(">>> 呼叫麻雀")
                mark2.call_sparrow__run()

            elif func_id == "send_mk2":
                print(">>> 送回载具")
                mark2.send_mk2__run()

            elif func_id == "call_whale":
                print(">>> 呼叫虎鲸")
                mark2.call_whale__run()

            elif func_id == "send_sparrow":
                print(">>> 送回麻雀")
                mark2.send_sparrow__run()

            elif func_id == "call_car":
                print(">>> 呼叫载具")
                mark2.call_car__run()

            elif func_id == "open_door":
                print(">>> 打开载具门")
                mark2.open_door__run()

            elif func_id == "call_mk2_truck":
                print(">>> 呼叫马克兔")
                mark2.call_mk2_truck__run()

            #---------战斗------------

            elif func_id == "snack":
                print(">>> 吃零食")
                fight.eat_snack()

            elif func_id == "pill":
                print(">>> 牛鲨睾酮")
                fight.eat_pill(sct=None)

            elif func_id == "bullet":
                print(">>> 子弹全满")
                fight.buy_bullet(sct=None)

            elif func_id == "revolver":
                print(">>> 连发左轮")
                fight.revolver()

            elif func_id == "rpg":
                print(">>> 连发重武器")
                fight.rpg()

            elif func_id == "shot":
                print(">>> 连发重武器")
                fight.sniper()

            elif func_id == "thermal":
                print(">>> 热成像")
                fight.thermal()

            elif func_id == "cloth":
                print(">>> 换衣服")
                fight.cloth()

            elif func_id == "flight_thermal":
                print(">>> 飞机热成像")
                fight.flight_thermal()

            elif func_id == "ghost":
                print(">>> 幽灵组织")
                fight.ghost()

#--------------------自定义按键宏--------------

            elif func_id == "script_0":
                print(">>> 运行按键宏0")
                custom_script.run_script_0()

            elif func_id == "script_1":
                print(">>> 运行按键宏1")
                custom_script.run_script_1()


            elif func_id == "script_2":
                print(">>> 运行按键宏2")
                custom_script.run_script_2()

            elif func_id == "script_3":
                print(">>> 运行按键宏3")
                custom_script.run_script_3()

            elif func_id == "script_4":
                print(">>> 运行按键宏4")
                custom_script.run_script_4()

            elif func_id == "script_5":
                print(">>> 运行按键宏5")
                custom_script.run_script_5()

            elif func_id == "script_6":
                print(">>> 运行按键宏6")
                custom_script.run_script_6()

            elif func_id == "script_7":
                print(">>> 运行按键宏7")
                custom_script.run_script_7()

            elif func_id == "script_8":
                print(">>> 运行按键宏8")
                custom_script.run_script_8()

            elif func_id == "script_9":
                print(">>> 运行按键宏9")
                custom_script.run_script_9()

            print(f"[V] 脚本 {func_id} 自然执行完毕")

        except SystemExit:
            # [新增] 这里捕获我们手动注入的异常，防止控制台报错
            print(f"[!] 脚本 {func_id} 已被新任务强制中断")
        except Exception as e:
            # 捕获其他未知错误
            print(f"[x] 脚本 {func_id} 发生未知错误: {e}")
        finally:
            # 可以在这里做一些清理工作，比如松开按键，防止卡键
            pass