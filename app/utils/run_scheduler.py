from datetime import datetime
import dateutil.rrule as dr
import dateutil.parser as dp
import dateutil.relativedelta as drel


class RunScheduler():

    frequencies = { 'Monthly' : dr.MONTHLY,
                    'Weekly' : dr.WEEKLY,
                    'Yearly' : dr.YEARLY}

    def __init__(self):
        pass

    def scheduler(self):
        start = datetime(2017,01,01)
        end = datetime(2017,12,31)
        next = dr.rrule(freq=dr.MONTHLY, interval=1, count=1,
                        bymonthday=25, dtstart=start, until=end)

        return [d.strftime('%d/%m/%Y') for d in next]

    def get_template_transactions(self, monthday, frequency, interval):
         today = datetime.now().date()
         # compare date created with today
         # check if rule is active
         # compare end date with today (if provided)

         next = dr.rrule(freq=self.frequencies[str(frequency)], interval=interval, count=1,
                         bymonthday=monthday, dtstart=today)

         return [d.date() for d in next]


    def get_template_transactions_with_start(self, monthday, frequency, interval, start):
         #today = datetime.now().date()

         next = dr.rrule(freq=self.frequencies[str(frequency)], interval=interval, count=1,
                         bymonthday=monthday, dtstart=start)

         return [d.date() for d in next]
