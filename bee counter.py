import os
import json
import time
import logging
import pymysql
import warnings
import datetime
import traceback
import Adafruit_DHT
import Adafruit_ADS1x15
from concurrent.futures import ThreadPoolExecutor

warnings.filterwarnings("ignore", category=RuntimeWarning, message="I2C frequency is not settable")

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename='test.log')
logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.DEBUG)

# # 增益設置
GAIN = 2/3
SPS = 860
buffer_size = 3
buffer = [[[] for _ in range(4)] for _ in range(8)]  # 每個通道的緩衝區

def DataBaseSender(data):
    db = pymysql.connect(host="140.112.94.59", user="root", password="taipower", db="110_bee_counter", port=33306)
    cursor = db.cursor()
#     sql = f"INSERT INTO bee_counter_test(id, time, hive_id, bee_in, bee_out, humid_in, humid_out, temp_in, temp_out) VALUES (NULL,'{datetime.datetime.now()}', 'test', '{str(data['bee_in'])}', '{str(data['bee_out'])}', 'str(data['humid_in']', 'str(data['humid_out']', 'str(data['temp_in']', 'str(data['t
    sql = f"INSERT INTO bee_counter_test(id, time, hive_id, bee_in, bee_out, humid_in, humid_out, temp_in, temp_out) VALUES (NULL,'{datetime.datetime.now()}', 'test', '{str(data['bee_in'])}', '{str(data['bee_out'])}', '0', '0', '0', '0')"

    try:
        cursor.execute(sql)
        db.commit()
        logging.info("Insert success")
        data['time'] = str(datetime.datetime.now())
        WriteJson(data, '/home/pi/unsend.json')
        
    except Exception as e:
        data['time'] = str(datetime.datetime.now())        
        WriteJson(data, '/home/pi/unsend.json')
        logging.error(traceback.format_exc())
        
    finally:
        if db:
            db.close()

def Classify(my_list):
    even, odd = my_list[::2], my_list[1::2]
    return even, odd

def Count(Merged):
    counter_in = 0
    counter_out = 0
    
    # 遍歷每個通道
    for i in range(len(Merged)):
        # print("i", i)
        j = 0  # 初始化索引
        while j < (len(Merged[i])):
#             print("j", j)
            if Merged[i][j] > 0:  # 當前值為正
                sub_sequence = Merged[i][j:]  # 從當前索引切割子序列
                matched = False
#                 print(i,sub_sequence)
                
                if sub_sequence[0:4] == [1, 2, -1, -2]:
                    matched = True
                    counter_out += 1
                    print(f"Channel {i}: Out", datetime.datetime.now())
                    Merged[i] = []
                        
                if sub_sequence[0:4] == [1, -1, 2, -2]:
                    matched = True
                    counter_out += 1
                    print(f"Channel {i}: Out", datetime.datetime.now())
                    Merged[i] = []
                                       
                if sub_sequence[0:4] == [2, 1, -2, -1]:
                    matched = True
                    counter_in += 1
                    print(f"Channel {i}: In", datetime.datetime.now())
                    Merged[i] = []
       
                if sub_sequence[0:4] == [2, -2, 1, -1]:
                    matched = True
                    counter_in += 1
                    print(f"Channel {i}: In", datetime.datetime.now())
                    Merged[i] = []
                              
#                 if not matched:
#                     counter_in, counter_out = process_sub_sequence(Merged, i, j, sub_sequence, counter_in, counter_out)
                
                if not matched:
                        j += 1  # 若未匹配，移動到下一個值
            else:
                j += 1  # 當前值為非正值，直接移動索引
                
    return counter_in, counter_out

def process_sub_sequence(Merged, i, j, sub_sequence, counter_in, counter_out):
    if len(sub_sequence) >= 4:
        remove_in, count_in = Match(sub_sequence, [2, 1, -2, -1])
        
        if count_in > 0:  # 當找到匹配時
            counter_in += count_in
            for index in reversed(remove_in):  # 反向刪除避免影響索引
                del Merged[i][j + index]
            print(f"Channel {i}: In", datetime.datetime.now())
#             counter_in, counter_out = process_sub_sequence(Merged, i, j, sub_sequence, counter_in, counter_out)
            return counter_in, counter_out

    if len(sub_sequence) >= 4:
        remove_in, count_in = Match(sub_sequence, [2, -2, 1, -1])
        counter_in += count_in
        
        if count_in > 0:  # 當找到匹配時
            for index in reversed(remove_in):  # 反向刪除避免影響索引
                del Merged[i][j + index]
            print(f"Channel {i}: In", datetime.datetime.now())
#             counter_in, counter_out = process_sub_sequence(Merged, i, j, sub_sequence, counter_in, counter_out)
            return counter_in, counter_out
            
    if len(sub_sequence) >= 4:
        remove_out, count_out = Match(sub_sequence, [1, 2, -1, -2])
        counter_out += count_out
        
        if count_out > 0:
            for index in reversed(remove_out):
                del Merged[i][j + index]
            print(f"Channel {i}: Out", datetime.datetime.now())
#             counter_in, counter_out = process_sub_sequence(Merged, i, j, sub_sequence, counter_in, counter_out)
            return counter_in, counter_out
            
    if len(sub_sequence) >= 4:
        remove_out, count_out = Match(sub_sequence, [1, -1, 2, -2])
        
        if count_out > 0:
            counter_out += count_out
            for index in reversed(remove_out):
                del Merged[i][j + index]
            print(f"Channel {i}: Out", datetime.datetime.now())
#             counter_in, counter_out = process_sub_sequence(Merged, i, j, sub_sequence, counter_in, counter_out)
            return counter_in, counter_out

    return counter_in, counter_out  # 若無匹配，返回原始計數器

def WriteJson(new_data, filepath):
    try:
        with open(filepath, 'r') as file:
            try:
                file_data = json.load(file)
            except json.JSONDecodeError:
                file_data = {}  # 如果檔案為空或損壞，初始化為空字典
    except FileNotFoundError:
        file_data = {}

    if "data" not in file_data:
        file_data["data"] = []

    file_data["data"].append(new_data)

    with open(filepath, 'w') as file:
        json.dump(file_data, file)

def truncate(num, n):
    integer = int(num * (10 ** n)) / (10 ** n)
    return float(integer)

def Match(sequence, pair):
    # print(sequence, pair)
    count = 0
    pair_index = 0  # 追踪當前匹配的 pair 索引
    remove = []

    for i in range(len(sequence)):  # 正確遍歷整個序列
        if sequence[i] == pair[pair_index]:
            # print(f'{sequence[i]} = {pair[pair_index]}')
            # print('i:',i)
            pair_index += 1  # 匹配到配對元素
            remove.append(i)

            if pair_index == len(pair):  # 完成完整配對
                count += 1
                pair_index = 0  # 重置索引繼續匹配
            
    return remove, count

def GetData(even_state_prev, odd_state_prev, even_changes, odd_changes, merged_changes, even_dynamic_normal, odd_dynamic_normal, start_time, acc_in, acc_out):
    THRESHOLD = 20000
    max_size = 15
    TIMEOUT_DURATION = 3

    values = [[0] * 4 for _ in range(8)]
    merged = {i: [] for i in range(16)}
    add_odd = False
    add_even = False
    last_change_time = {i: datetime.datetime.now() for i in range(16)}

    even_normal_buffer = {i: [] for i in range(16)}
    odd_normal_buffer = {i: [] for i in range(16)}
    NORMAL_BUFFER_SIZE = 10

    adc1_0 = Adafruit_ADS1x15.ADS1115(address=0x48, busnum = 1)  
    adc1_1 = Adafruit_ADS1x15.ADS1115(address=0x49, busnum = 1)  
    adc1_2 = Adafruit_ADS1x15.ADS1115(address=0x4a, busnum = 1)  
    adc1_3 = Adafruit_ADS1x15.ADS1115(address=0x4b, busnum = 1)  
    adc2_0 = Adafruit_ADS1x15.ADS1115(address=0x48, busnum = 3)  
    adc2_1 = Adafruit_ADS1x15.ADS1115(address=0x49, busnum = 3)  
    adc3_0 = Adafruit_ADS1x15.ADS1115(address=0x48, busnum = 4)  
    adc3_1 = Adafruit_ADS1x15.ADS1115(address=0x49, busnum = 4)  
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        while True:
            futures = []
            for i in range(4):
                for j, adc in enumerate([adc1_0, adc1_1, adc1_2, adc1_3, adc2_0, adc2_1, adc3_0, adc3_1]):
                    futures.append((j, i, executor.submit(adc.read_adc, i, gain=GAIN, data_rate=SPS)))

            for j, i, future in futures:
                try:
                    result = future.result()
                    if 0 <= result <= 32767:
                        buffer[j][i].append(result)
                        if len(buffer[j][i]) > buffer_size:
                            buffer[j][i].pop(0)
                        values[j][i] = sum(buffer[j][i]) // len(buffer[j][i])
                    else:
                        values[j][i] = -1
                        print(f"Invalid reading from ADC {j}, channel {i}: {result}")
                except Exception as e:
                    values[j][i] = -1
                    print(f"Error reading ADC {j}, channel {i}: {e}")

            T1 = [values[j][i] for j in range(8) for i in range(4)]
            even_T1, odd_T1 = Classify(T1)

            for i in range(16):
                if even_T1[i] > THRESHOLD:
                    even_state = 1
                elif (even_dynamic_normal[i] -20) < even_T1[i] < (even_dynamic_normal[i] + 20):
                    even_state = -1

                if odd_T1[i] > THRESHOLD:
                    odd_state = 2
                elif (odd_dynamic_normal[i] -20) < odd_T1[i] < (odd_dynamic_normal[i] + 20):
                    odd_state = -2

                if even_state_prev[i] != even_state and i not in (0,1,2,3,4,5,6,7):
                    index = i
                    add_even = True
                    last_change_time[i] = datetime.datetime.now()
                    even_state_prev[i] = even_state
                    if not even_changes[i]:
                        even_changes[i].append((even_state, datetime.datetime.now()))
                    else:
                        even_changes[i][-1] = (even_state, datetime.datetime.now())

                if odd_state_prev[i] != odd_state and i not in (0,1,2,3,4,5,6,7):
                    add_odd = True
                    last_change_time[i] = datetime.datetime.now()
                    index = i
                    odd_state_prev[i] = odd_state
                    if not odd_changes[i]:
                        odd_changes[i].append((odd_state, datetime.datetime.now()))
                    else:
                        odd_changes[i][-1] = (odd_state, datetime.datetime.now())

                if (datetime.datetime.now() - last_change_time[i]).total_seconds() > TIMEOUT_DURATION:
                    merged_changes[i] = []

                if add_even or add_odd:
                    merged[index] = (even_changes[index] + odd_changes[index])
                    merged[index] = sorted(merged[index], key=lambda x: x[1])
                    merged_changes[index].extend([change[0] for change in merged[index]])

                    if len(merged_changes[index]) > max_size:
                        merged_changes[index] = merged_changes[index][-max_size:]

#                     print(f"Merged Changes: {merged_changes}")

                    if add_even:
                        even_changes[index] = []

                    if add_odd:
                        odd_changes[index] = []

                    add_even = False
                    add_odd = False

                    counter_in, counter_out = Count(merged_changes)
                    acc_in += counter_in
                    acc_out += counter_out

                pass_time = (datetime.datetime.now() - start_time).total_seconds()
    #             print(pass_time)
                
                if pass_time > 60:
                    data = {"bee_in": acc_in, "bee_out": acc_out}
                    print(data)
                    DataBaseSender(data)
                    start_time = datetime.datetime.now()
                    acc_in, acc_out = 0, 0
                    return start_time
            
def main():
    even_state_prev = [0] * 16
    odd_state_prev = [0] * 16
    even_changes = {i: [] for i in range(16)}  # 每個通道的 even 狀態變化
    odd_changes = {i: [] for i in range(16)}   # 每個通道的 odd 狀態變化
    merged_changes = {i: [] for i in range(16)}  # 用來儲存每個通道的合併變化資料
    start_time = datetime.datetime.now()
    acc_in, acc_out = 0, 0
    THRESHOLD = 6000
    
    even_dynamic_normal = {i: 0 for i in range(16)}
    odd_dynamic_normal = {i: 0 for i in range(16)}
    
    values = [[0] * 4 for _ in range(8)]  # 假設每個 ADC 有 4 個 channel
    buffer = {j: {i: [] for i in range(4)} for j in range(8)}  # 每個 ADC 每個通道都有一個緩衝區
    
    # 初始化多個 ADS1115 ADC 實例
    adc1_0 = Adafruit_ADS1x15.ADS1115(address=0x48, busnum = 1)  
    adc1_1 = Adafruit_ADS1x15.ADS1115(address=0x49, busnum = 1)  
    adc1_2 = Adafruit_ADS1x15.ADS1115(address=0x4a, busnum = 1)  
    adc1_3 = Adafruit_ADS1x15.ADS1115(address=0x4b, busnum = 1)  
    adc2_0 = Adafruit_ADS1x15.ADS1115(address=0x48, busnum = 3)  
    adc2_1 = Adafruit_ADS1x15.ADS1115(address=0x49, busnum = 3)  
    adc3_0 = Adafruit_ADS1x15.ADS1115(address=0x48, busnum = 4)  
    adc3_1 = Adafruit_ADS1x15.ADS1115(address=0x49, busnum = 4)  

    with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for i in range(4):
                for j, adc in enumerate([adc1_0, adc1_1, adc1_2, adc1_3, adc2_0, adc2_1, adc3_0, adc3_1]):
                    futures.append((j, i, executor.submit(adc.read_adc, i, gain=GAIN, data_rate=SPS)))

            for j, i, future in futures:
                try:
                    result = future.result()
                    if 0 <= result <= 32767:
                        buffer[j][i].append(result)
                        if len(buffer[j][i]) > buffer_size:
                            buffer[j][i].pop(0)
                        values[j][i] = sum(buffer[j][i]) // len(buffer[j][i])
                    else:
                        values[j][i] = -1
                        print(f"Invalid reading from ADC {j}, channel {i}: {result}")
                except Exception as e:
                    values[j][i] = -1
                    print(f"Error reading ADC {j}, channel {i}: {e}")  

    T1 = [values[j][i] for j in range(8) for i in range(4)]
    even_T1, odd_T1 = Classify(T1)
            
    for i in range(16):
        # 只存储小于阈值的数据
        if odd_dynamic_normal[i] == 0 and odd_T1[i] < 1500:
            odd_dynamic_normal[i] = odd_T1[i]

        if even_dynamic_normal[i] == 0 and even_T1[i] < 1500:
            even_dynamic_normal[i] = even_T1[i]

    
    print("Even Dynamic Normal:", even_dynamic_normal)
    print("Odd Dynamic Normal:", odd_dynamic_normal)

    while True:
        try:
            start_time = GetData(even_state_prev, odd_state_prev, even_changes, odd_changes, merged_changes, even_dynamic_normal, odd_dynamic_normal,start_time, acc_in, acc_out)

        except Exception as e:
            logger.error(f"Critical error: {traceback.format_exc()}")
            logger.info("Restarting main loop...")

        
if __name__ == "__main__":
    main()