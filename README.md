# Description

Tool lấy lịch bận của mọi người và chia lịch sao cho mỗi buổi học đều có số người >= 1 ngưỡng cho trước, sử dụng thuật toán luồng cực đại(https://vnoi.info/wiki/translate/wcipeg/Flows) để xây dựng lịch học dựa trên lịch bận của thành viên.

Một nhóm có rất đông sinh viên, các sinh viên được phân vào n nhóm, mỗi nhóm học 2 buổi trong tuần.

Với các yêu cầu : 

1. trong 1 nhóm phải có >= x người (trong code sử dụng x=7).
2. 1 nhóm phải học cách nhau ít nhất là 1 ngày
3. lịch học phải phù hợp lịch bận của giảng viên.

# SETUP

1. python -m venv env

2. pip install requirements.txt: câu lệnh để cài tất cả các package cần thiết trong code

5. python main.py lich.csv index.csv limit_depth answer.txt (kết quả in ra màn hình là kết quả đã tối ưu nhất có thể)

lich.csv là file con của lịch bận, chỉ chứa lịch bận và không kèm bất kỳ thông tin gì khác

index.csv la file chứa ký hiệu tên của mọi người

limit_depth : nên lấy <= 10^5, hoac <=10^4

answer.txt: là file chứa các trường hợp sinh được (nhưng có thể chưa là tối ưu nhất)

# MADE BY PHUONG NAM FROM PROPTIT WITH LOVE <3
