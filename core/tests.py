from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from datetime import timedelta, date

from .models import Profile, OTP, Appointment, CertificateRequest
from .forms import StudentRegistrationForm


class ModelsTestCase(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="alice", email="alice@cvsu.edu.ph", password="pass")
		self.profile = Profile.objects.create(user=self.user, student_number="S123", course="CS", year_level="1st Year")

	def test_profile_str(self):
		s = str(self.profile)
		self.assertIn(self.user.username, s)
		self.assertIn(self.profile.student_number, s)

	def test_otp_is_expired(self):
		otp_future = OTP.objects.create(user=self.user, code="111111", expires_at=timezone.now() + timedelta(minutes=10))
		otp_past = OTP.objects.create(user=self.user, code="222222", expires_at=timezone.now() - timedelta(minutes=10))
		self.assertFalse(otp_future.is_expired())
		self.assertTrue(otp_past.is_expired())

	def test_appointment_and_certificate_str(self):
		appt = Appointment.objects.create(student=self.user, purpose="Meet", appointment_date=date.today(), appointment_time=timezone.now().time())
		self.assertIn(self.user.username, str(appt))
		cert = CertificateRequest.objects.create(student=self.user, certificate_type='good_moral', purpose='For internship')
		self.assertIn(self.user.username, str(cert))


class FormsTestCase(TestCase):
	def setUp(self):
		# create an existing profile to test unique student number check
		self.existing_user = User.objects.create_user(username="bob", email="bob@cvsu.edu.ph", password="pw")
		Profile.objects.create(user=self.existing_user, student_number="S999")

	def test_student_registration_email_domain_validation(self):
		data = {
			"username": "newstu",
			"email": "new@student.com",
			"password": "p",
			"confirm_password": "p",
			"student_number": "S100",
			"course": "CS",
			"year_level": "1st Year",
			"first_name": "New",
			"last_name": "Student",
		}
		form = StudentRegistrationForm(data=data)
		self.assertFalse(form.is_valid())
		self.assertIn('email', form.errors)

	def test_student_registration_password_mismatch(self):
		data = {
			"username": "newstu2",
			"email": "good@cvsu.edu.ph",
			"password": "p1",
			"confirm_password": "p2",
			"student_number": "S101",
			"course": "CS",
			"year_level": "1st Year",
			"first_name": "A",
			"last_name": "B",
		}
		form = StudentRegistrationForm(data=data)
		self.assertFalse(form.is_valid())
		# non-field error from clean
		self.assertTrue('__all__' in form.errors or forms_error_contains(form, "Password"))

	def test_student_registration_student_number_unique(self):
		data = {
			"username": "someone",
			"email": "someone@cvsu.edu.ph",
			"password": "pw",
			"confirm_password": "pw",
			"student_number": "S999",  # already exists
			"course": "CS",
			"year_level": "1st Year",
			"first_name": "A",
			"last_name": "B",
		}
		form = StudentRegistrationForm(data=data)
		self.assertFalse(form.is_valid())
		self.assertIn('student_number', form.errors)


def forms_error_contains(form, substr):
	"""Helper to check if any error message contains substr."""
	for k, v in form.errors.items():
		for msg in v:
			if substr in msg:
				return True
	return False


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', DEFAULT_FROM_EMAIL='test@example.com')
class ViewsIntegrationTestCase(TestCase):
	def setUp(self):
		self.client = Client()
		# a regular user
		self.user = User.objects.create_user(username='stu', email='stu@cvsu.edu.ph', password='pw')
		self.profile = Profile.objects.create(user=self.user, student_number='S200', submitted_at=timezone.now())

		# a staff user for approver actions
		self.staff = User.objects.create_user(username='staff', email='staff@cvsu.edu.ph', password='pw', is_staff=True)

	def test_register_view_renders(self):
		resp = self.client.get(reverse('core:register'))
		self.assertEqual(resp.status_code, 200)

	def test_student_dashboard_redirects_if_not_approved(self):
		self.client.force_login(self.user)
		resp = self.client.get(reverse('core:student_dashboard'))
		# Should redirect to pending approval
		self.assertEqual(resp.status_code, 302)
		self.assertIn(reverse('core:pending_approval'), resp.url)

	def test_verify_otp_success_flow(self):
		# create user and otp
		u = User.objects.create_user(username='vuser', email='vuser@cvsu.edu.ph', password='pw')
		Profile.objects.create(user=u, student_number='S777')
		otp = OTP.objects.create(user=u, code='555555', expires_at=timezone.now() + timedelta(minutes=30))

		session = self.client.session
		session['verify_user_id'] = u.id
		session.save()

		resp = self.client.post(reverse('core:verify_otp'), {'code': '555555'})

		# After successful verification, should redirect to pending approval
		self.assertEqual(resp.status_code, 302)
		self.assertIn(reverse('core:pending_approval'), resp.url)

		# Profile should be marked verified and OTPs deleted
		u.refresh_from_db()
		self.assertTrue(u.profile.is_verified_email)
		self.assertFalse(OTP.objects.filter(user=u).exists())

	def test_appointment_create_and_double_booking(self):
		self.client.force_login(self.user)
		today_str = date.today().isoformat()
		# initial create
		resp = self.client.post(reverse('core:student_appointments'), {
			'purpose': 'Meet',
			'appointment_date': today_str,
			'appointment_time': '09:00'
		}, follow=True)
		self.assertEqual(resp.status_code, 200)
		self.assertTrue(Appointment.objects.filter(student=self.user, appointment_date=today_str).exists())

		# second attempt same date should be prevented
		resp2 = self.client.post(reverse('core:student_appointments'), {
			'purpose': 'Another',
			'appointment_date': today_str,
			'appointment_time': '10:00'
		}, follow=True)
		# Should still redirect and not create a second appointment for same date
		self.assertEqual(resp2.status_code, 200)
		self.assertEqual(Appointment.objects.filter(student=self.user, appointment_date=today_str).count(), 1)

	def test_appointment_daily_limit(self):
		# create 10 different students with appointments on same date
		target_date = date.today()
		for i in range(10):
			u = User.objects.create_user(username=f'user{i}', email=f'u{i}@cvsu.edu.ph', password='pw')
			Profile.objects.create(user=u, student_number=f'U{i}')
			Appointment.objects.create(student=u, purpose='p', appointment_date=target_date, appointment_time=timezone.now().time())

		# now logging in as a new student and trying to book same date should fail
		new_user = User.objects.create_user(username='newu', email='newu@cvsu.edu.ph', password='pw')
		Profile.objects.create(user=new_user, student_number='S888')
		self.client.force_login(new_user)
		resp = self.client.post(reverse('core:student_appointments'), {
			'purpose': 'Late',
			'appointment_date': target_date.isoformat(),
			'appointment_time': '08:00'
		}, follow=True)
		self.assertEqual(resp.status_code, 200)
		# no appointment created for new user
		self.assertFalse(Appointment.objects.filter(student=new_user, appointment_date=target_date).exists())

	def test_certificate_request_submission(self):
		self.client.force_login(self.user)
		resp = self.client.post(reverse('core:certificate_request'), {
			'certificate_type': 'good_moral',
			'purpose': 'For job'
		}, follow=True)
		self.assertEqual(resp.status_code, 200)
		self.assertTrue(CertificateRequest.objects.filter(student=self.user, certificate_type='good_moral').exists())

	def test_approve_and_reject_profile_by_staff(self):
		# create a profile pending approval
		u = User.objects.create_user(username='toapprove', email='ta@cvsu.edu.ph', password='pw')
		prof = Profile.objects.create(user=u, student_number='S321', submitted_at=timezone.now(), is_verified_email=True)

		# staff approves
		self.client.force_login(self.staff)
		resp = self.client.post(reverse('core:approve_profile', args=[prof.id]), follow=True)
		self.assertEqual(resp.status_code, 200)
		prof.refresh_from_db()
		self.assertTrue(prof.is_approved_by_registrar)
		# email should have been sent (locmem)
		self.assertGreaterEqual(len(mail.outbox), 1)

		# now reject (create another profile to reject)
		u2 = User.objects.create_user(username='toreject', email='tr@cvsu.edu.ph', password='pw')
		prof2 = Profile.objects.create(user=u2, student_number='S322', submitted_at=timezone.now(), is_verified_email=True)
		resp2 = self.client.post(reverse('core:reject_profile', args=[prof2.id]), follow=True)
		self.assertEqual(resp2.status_code, 200)
		prof2.refresh_from_db()
		u2.refresh_from_db()
		self.assertFalse(prof2.is_approved_by_registrar)
		self.assertFalse(u2.is_active)
		self.assertGreaterEqual(len(mail.outbox), 2)

