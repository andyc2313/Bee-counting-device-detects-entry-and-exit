# Bee-counting-device-detects-entry-and-exit
#Bee Movement Detection System

This project is designed to monitor the entry and exit movements of bees using infrared sensors and ADS1115 ADC modules. The data is stored in a database for further analysis. The system detects bee entry and exit events based on sensor input and tracks the count of bees entering or leaving the hive.

## Features

- **Infrared Sensors**: Reads data from infrared sensors via ADS1115 modules to detect bee entry and exit events.
- **Database Storage**: Stores entry and exit data in a MySQL database for easy analysis.
- **Data Buffering**: Uses a buffer to handle continuous sensor data and prevent false readings.
- **Error Handling**: Handles invalid or erroneous sensor data by writing unsent data to a local JSON file.

## Requirements

- Python 3.x
- [Adafruit_ADS1x15](https://pypi.org/project/Adafruit-ADS1x15/) - for communication with the ADS1115 ADC
- [Adafruit_DHT](https://pypi.org/project/Adafruit-DHT/) - for reading temperature and humidity sensor data (if applicable)
- [pymysql](https://pypi.org/project/PyMySQL/) - for connecting to MySQL database
- [ThreadPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor) - for concurrent processing of multiple sensor data inputs

## Installation

1. Install Python dependencies:

```bash
pip install Adafruit-ADS1x15 Adafruit-DHT pymysql
```

2. Ensure your Raspberry Pi is connected to the infrared sensors and ADS1115 modules.

3. Set up the MySQL database. The project will store data in a table named `bee_counter_test`. Please create the database and define the table structure as shown below.

4. Configure database connection settings:

Edit the `DataBaseSender` function and update the `db = pymysql.connect()` parameters with the correct database IP, username, password, etc.

## Usage

1. Run the main program:

The program will continuously read sensor data, detect entry and exit events, and store the results in the database every minute.

2. Every minute, the program will insert `bee_in` and `bee_out` data into the database. It will also write any unsent data to a local JSON file located at `/home/pi/unsend.json`.

## Configuration

- **Gain Settings**: The gain (`GAIN`) is set to `2/3`, which is suitable for standard infrared sensors.
- **Read Speed**: The program is set to read sensor data 860 times per second (`SPS`).
- **Threshold Settings**: The `THRESHOLD` value is set to 6000, meaning any reading above this value will be considered as a bee entering or exiting.

## Database Table Structure

Ensure your database has the following table structure:

```sql
CREATE TABLE `bee_counter_test` (
`id` INT AUTO_INCREMENT PRIMARY KEY,
`time` DATETIME,
`hive_id` 
`bee_in` INT,
`bee_out` INT,
`humid_in` FLOAT,
`humid_out` FLOAT,
`temp_in` FLOAT,
`temp_out` FLOAT
);


## Logging

All log messages (e.g., database insert results, errors) are recorded in the `test.log` file and can be reviewed as needed.

## Parameters

- **`GAIN`**: Gain setting that controls the sensitivity of the sensor readings.
- **`SPS`**: Samples per second, controlling the frequency of sensor updates.
- **`buffer_size`**: Size of the buffer for each channel.
- **`TIMEOUT_DURATION`**: Used to filter out unchanged data from channels.
