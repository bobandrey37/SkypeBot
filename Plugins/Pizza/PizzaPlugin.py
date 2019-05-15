import math
from skpy import SkypeNewMessageEvent, SkypeEditMessageEvent

from Core.PluginBase import PluginBase
from .Command import Command


class PizzaPlugin(PluginBase):
    def __init__(self, skype):
        super(PizzaPlugin, self).__init__(skype=skype)
        self._orders = []
        self._started_by = None
        self._is_stopped = False
        self._NUMBER_OF_PIZZA_SLICES = 8

    def friendly_name(self):
        return 'Pizza plugin'

    def version(self):
        return '0.1'

    def keywords(self):
        return ['pizza']

    def handle(self, event):
        if not isinstance(event, SkypeNewMessageEvent) and not isinstance(event, SkypeEditMessageEvent):
            return

        message = event.msg
        command = Command.parse(message=message.markup)

        if self._process_if_help_command(message=message, command=command):
            return

        self._ensure_exactly_one_command_is_given(command=command)

        if command.start:
            self._handle_start(message=message, command=command)
        elif command.stop:
            self._handle_stop(message=message, command=command)
        elif command.cost is not None:
            self._handle_cost(message=message, command=command)
        elif command.number_of_slices:
            self._handle_number_of_slices(message=message, command=command)

    def help_message(self):
        return """{friendly_name} v{version}

Keywords: {keywords}
Commands:
    #help
    #start
    #stop
    #cost
    NUMBER_OF_SLICES
""".format(friendly_name=self.friendly_name(),
           version=self.version(),
           keywords=','.join(['#' + keyword for keyword in self.keywords()])
           )

    def _process_if_help_command(self, message, command):
        if command.help:
            self._skype.contacts[message.userId].chat.sendMsg(self.help_message())

        return command.help

    @staticmethod
    def _ensure_exactly_one_command_is_given(command):
        commands_number = 0
        commands_number += 1 if command.start else 0
        commands_number += 1 if command.stop else 0
        commands_number += 1 if command.cost is not None else 0
        commands_number += 1 if command.number_of_slices else 0

        if commands_number != 1:
            raise Exception("You have to specify exactly one command at once")

    def _handle_start(self, message, command):
        if self._started_by:
            raise Exception("Exactly one #pizza can be started at the same time")

        self._orders = []
        self._started_by = message.user
        self._is_stopped = False

        self._skype.contacts[message.user.id].chat.sendMsg(
            "You've started #pizza at {time} UTC. Please remember to #pizza #stop".format(time=str(message.time.replace(microsecond=0)))
        )

    def _handle_stop(self, message, command):
        if not self._started_by:
            raise Exception("No #pizza is currently started")

        if self._started_by.id != message.userId:
            raise Exception("Only user which started #pizza can stop it")

        if self._is_stopped:
            raise Exception("#pizza is already stopped")

        self._is_stopped = True

        final_order = list(self._orders)
        total_ordered_slices = sum(order[1] for order in final_order)
        number_of_pizzas = int(total_ordered_slices / self._NUMBER_OF_PIZZA_SLICES)
        slices_overflow = total_ordered_slices % self._NUMBER_OF_PIZZA_SLICES

        if slices_overflow:
            for idx, order in reversed(list(enumerate(self._orders))):
                if order[1] <= slices_overflow:
                    final_order.pop(idx)
                    slices_overflow -= order[1]
                    self._skype.contacts[order[0].id].chat.sendMsg(
                        "Sorry, you were removed from #pizza order, because of rounding to whole pizzas :("
                    )
                else:
                    new_slices = final_order[idx][1] - slices_overflow
                    final_order[idx] = (final_order[idx][0], new_slices)
                    slices_overflow = 0
                    self._skype.contacts[order[0].id].chat.sendMsg(
                        "Sorry, your #pizza order was reduced to {slices} slice(s), because of rounding to whole pizzas :(".format(slices=new_slices)
                    )

                if not slices_overflow:
                    break

        self._orders = final_order
        orders_summaries = ["{user_name} ({user_id}) - {slices}".format(user_name=order[0].name, user_id=order[0].id, slices=order[1]) for order in self._orders]

        self._skype.contacts[message.userId].chat.sendMsg(
            """You've stopped #pizza at {time} UTC. Please remember to #pizza #cost
            
Summary:
Pizzas to order: {pizzas}
{orders_summaries}
""".format(time=str(message.time.replace(microsecond=0)),
           pizzas=number_of_pizzas,
           orders_summaries="\n".join(orders_summaries))
        )

    def _handle_cost(self, message, command):
        if not self._started_by:
            raise Exception("No #pizza is currently started")

        if self._started_by.id != message.userId:
            raise Exception("Only user which started #pizza can 'cost' it")

        total_ordered_slices = sum(order[1] for order in self._orders)
        if total_ordered_slices:
            slice_cost = command.cost / total_ordered_slices

            pay_command = [
                "#pay",
                "#blik TELEPHONE_NUMBER",
                "#acc_number ACCOUNT_NUMBER",
                "#acc_name {}".format(message.user.name),
                "#title Pizza"
            ]

            for order in self._orders:
                skype_id = "me" if order[0].id == message.userId else order[0].id
                amount = math.ceil(order[1] * slice_cost) / 100
                pay_command.append("@{} {}".format(skype_id, amount))

            self._skype.contacts[message.userId].chat.sendMsg("\n".join(pay_command))

        self._orders = []
        self._started_by = None
        self._is_stopped = False

    def _handle_number_of_slices(self, message, command):
        if not self._started_by or self._is_stopped:
            raise Exception("No #pizza is currently started")

        existing_idx = [idx for idx, order in enumerate(self._orders) if order[0].id == message.userId]

        if existing_idx:
            self._orders.pop(existing_idx[0])

        self._orders.append((message.user, command.number_of_slices))
        total_ordered_slices = sum(order[1] for order in self._orders)
        missing_slices = self._NUMBER_OF_PIZZA_SLICES - total_ordered_slices % self._NUMBER_OF_PIZZA_SLICES

        self._skype.contacts[message.userId].chat.sendMsg("You've registered for {no_slices} #pizza slice(s)".format(no_slices=command.number_of_slices))
        message.chat.sendMsg("{missing_slices} slice(s) are missing for the next #pizza".format(missing_slices=missing_slices))
