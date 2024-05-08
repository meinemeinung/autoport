import argparse
import os
import datetime as dt
from autoport import Portfolio

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('date', help='Date in %Y%m%d format')
    parser.add_argument('source', nargs='+', help='List of source files to process separated by spaces')
    parser.add_argument('--config', default='./config/config-indo.ini')
    parser.add_argument('--target', default='')

    args = parser.parse_args()
    return args

def main():
    args = get_args()
    
    if not args.date is None:
        date = dt.datetime.strptime(args.date, '%Y%m%d')
    else:
        date = dt.datetime.now()
        
    for i, file in enumerate(args.source):
        filename = os.path.basename(file)

        port = Portfolio(
            file_path=file,
            config_path=args.config,
            start_date=dt.datetime(2022, 12, 30),
            end_date=date
        )
        port.process_all()
        port.export_to_excel(os.path.join(args.target, filename))

if __name__=='__main__':
    main()
